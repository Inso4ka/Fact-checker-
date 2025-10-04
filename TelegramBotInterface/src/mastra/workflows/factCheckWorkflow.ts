import { createWorkflow, createStep } from "../inngest";
import { z } from "zod";
import { factCheckAgent } from "../agents/factCheckAgent";

const step1 = createStep({
  id: "use-agent",
  inputSchema: z.object({
    message: z.string(),
    chatId: z.number(),
    processingMessageId: z.number().nullable().optional(),
  }),
  outputSchema: z.object({
    response: z.string(),
    chatId: z.number(),
    processingMessageId: z.number().nullable().optional(),
  }),
  execute: async ({ inputData, mastra }) => {
    const logger = mastra?.getLogger();
    logger?.info("🔍 [Step1] Starting fact-check with agent", {
      message: inputData.message,
    });

    try {
      const { text } = await factCheckAgent.generate(
        [{ role: "user", content: inputData.message }],
        {
          maxSteps: 5,
        }
      );

      logger?.info("✅ [Step1] Fact-check completed", {
        responseLength: text.length,
      });

      return {
        response: text,
        chatId: inputData.chatId,
        processingMessageId: inputData.processingMessageId,
      };
    } catch (error) {
      logger?.error("❌ [Step1] Error during fact-check", { 
        error: error instanceof Error ? error.message : String(error),
        stack: error instanceof Error ? error.stack : undefined 
      });
      throw error;
    }
  },
});

const step2 = createStep({
  id: "send-reply",
  inputSchema: z.object({
    response: z.string(),
    chatId: z.number(),
    processingMessageId: z.number().nullable().optional(),
  }),
  outputSchema: z.object({
    sent: z.boolean(),
  }),
  execute: async ({ inputData, mastra }) => {
    const logger = mastra?.getLogger();
    const MAX_MESSAGE_LENGTH = 4096;
    
    logger?.info("📤 [Step2] Sending reply to Telegram", {
      chatId: inputData.chatId,
      responseLength: inputData.response.length,
    });

    const botToken = process.env.TELEGRAM_BOT_TOKEN;
    if (!botToken) {
      logger?.error("❌ [Step2] TELEGRAM_BOT_TOKEN not found");
      throw new Error("TELEGRAM_BOT_TOKEN is not configured");
    }

    try {
      // Delete processing indicator message first
      if (inputData.processingMessageId) {
        try {
          await fetch(
            `https://api.telegram.org/bot${botToken}/deleteMessage`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                chat_id: inputData.chatId,
                message_id: inputData.processingMessageId,
              }),
            }
          );
          logger?.info("🗑️ [Step2] Processing indicator deleted", {
            messageId: inputData.processingMessageId,
          });
        } catch (error) {
          logger?.error("❌ [Step2] Failed to delete processing indicator", {
            error,
          });
        }
      }
      // Split message into chunks if too long
      const chunks: string[] = [];
      if (inputData.response.length <= MAX_MESSAGE_LENGTH) {
        chunks.push(inputData.response);
      } else {
        logger?.info("📦 [Step2] Message too long, splitting into chunks", {
          totalLength: inputData.response.length,
        });
        
        let remainingText = inputData.response;
        while (remainingText.length > 0) {
          if (remainingText.length <= MAX_MESSAGE_LENGTH) {
            chunks.push(remainingText);
            break;
          }
          
          // Find a good break point (newline, period, or space)
          let breakPoint = MAX_MESSAGE_LENGTH;
          const searchText = remainingText.substring(0, MAX_MESSAGE_LENGTH);
          
          const lastNewline = searchText.lastIndexOf('\n');
          const lastPeriod = searchText.lastIndexOf('.');
          const lastSpace = searchText.lastIndexOf(' ');
          
          if (lastNewline > MAX_MESSAGE_LENGTH * 0.7) {
            breakPoint = lastNewline + 1;
          } else if (lastPeriod > MAX_MESSAGE_LENGTH * 0.7) {
            breakPoint = lastPeriod + 1;
          } else if (lastSpace > MAX_MESSAGE_LENGTH * 0.7) {
            breakPoint = lastSpace + 1;
          }
          
          chunks.push(remainingText.substring(0, breakPoint));
          remainingText = remainingText.substring(breakPoint);
        }
        
        logger?.info("📦 [Step2] Split into chunks", { chunkCount: chunks.length });
      }

      // Send all chunks
      for (let i = 0; i < chunks.length; i++) {
        const chunk = chunks[i];
        const isLast = i === chunks.length - 1;
        
        logger?.info(`📤 [Step2] Sending chunk ${i + 1}/${chunks.length}`, {
          chunkLength: chunk.length,
        });

        const response = await fetch(
          `https://api.telegram.org/bot${botToken}/sendMessage`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              chat_id: inputData.chatId,
              text: chunk,
              parse_mode: "HTML",
            }),
          }
        );

        const data = await response.json();

        if (!response.ok || !data.ok) {
          logger?.error(`❌ [Step2] Failed to send chunk ${i + 1}`, { error: data });
          return { sent: false };
        }

        logger?.info(`✅ [Step2] Chunk ${i + 1}/${chunks.length} sent`, {
          messageId: data.result.message_id,
        });

        // Small delay between chunks to avoid rate limiting
        if (!isLast) {
          await new Promise(resolve => setTimeout(resolve, 100));
        }
      }

      logger?.info("✅ [Step2] All messages sent successfully");
      return { sent: true };
    } catch (error) {
      logger?.error("❌ [Step2] Error sending message", { error });
      throw error;
    }
  },
});

export const factCheckWorkflow = createWorkflow({
  id: "fact-check-workflow",
  description: "Проверка достоверности утверждений через Telegram",
  inputSchema: z.object({
    message: z.string(),
    chatId: z.number(),
    processingMessageId: z.number().nullable().optional(),
  }),
  outputSchema: z.object({
    sent: z.boolean(),
  }),
})
  .then(step1)
  .then(step2)
  .commit();
