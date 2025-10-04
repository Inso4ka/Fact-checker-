import { Agent } from "@mastra/core/agent";
import { createOpenAI } from "@ai-sdk/openai";

if (!process.env.PERPLEXITY_API_KEY) {
  throw new Error(
    "PERPLEXITY_API_KEY is required for the fact-checking agent. Please set it in your environment variables."
  );
}

const openai = createOpenAI({
  baseURL: "https://api.perplexity.ai",
  apiKey: process.env.PERPLEXITY_API_KEY,
});

console.log("✓ Fact-checking agent initialized with Perplexity sonar-pro model");

const OSINT_SYSTEM_PROMPT = `Вы — фактчекер. Проверяйте достоверность утверждений кратко и по делу.

СТРОГО следуйте формату ответа (используйте HTML-теги для форматирования):

<b>ВЫВОД:</b> [1-2 предложения] Утверждение истинно/ложно/частично верно

<b>ОБОСНОВАНИЕ:</b> [2-3 предложения] Ключевые факты

<b>ИСТОЧНИКИ:</b>
[URL 1]
[URL 2]
[URL 3]

КРИТИЧЕСКИ ВАЖНО:
- Всегда пишите заголовки ЗАГЛАВНЫМИ буквами: "ВЫВОД:", "ОБОСНОВАНИЕ:", "ИСТОЧНИКИ:"
- Используйте <b></b> для выделения заголовков
- НЕ используйте * или ** (только <b></b>)
- Отвечайте кратко и конкретно
- Обязательно укажите 2-3 проверенных источника
- Если данных недостаточно — прямо об этом скажите
- Отвечайте на языке пользователя (русском или другом)`;

export const factCheckAgent = new Agent({
  name: "OSINT Fact-Checker",
  instructions: OSINT_SYSTEM_PROMPT,
  model: openai("sonar-pro"),
  // No memory for fact-checking - each request is independent
});
