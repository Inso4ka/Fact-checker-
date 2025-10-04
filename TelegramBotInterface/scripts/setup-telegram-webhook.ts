import 'dotenv/config';

const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const REPLIT_DOMAINS = process.env.REPLIT_DOMAINS;

if (!TELEGRAM_BOT_TOKEN) {
  console.error('❌ TELEGRAM_BOT_TOKEN not found in environment');
  process.exit(1);
}

if (!REPLIT_DOMAINS) {
  console.error('❌ REPLIT_DOMAINS not found in environment');
  process.exit(1);
}

const webhookUrl = `https://${REPLIT_DOMAINS}/webhooks/telegram/action`;

console.log('🔧 Setting up Telegram webhook...');
console.log('📍 Webhook URL:', webhookUrl);

async function setupWebhook() {
  try {
    // Set webhook
    const setResponse = await fetch(
      `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: webhookUrl }),
      }
    );

    const setResult = await setResponse.json();
    console.log('✅ setWebhook response:', JSON.stringify(setResult, null, 2));

    // Get webhook info
    const infoResponse = await fetch(
      `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo`
    );

    const infoResult = await infoResponse.json();
    console.log('📋 Webhook info:', JSON.stringify(infoResult, null, 2));

    if (infoResult.result?.url === webhookUrl) {
      console.log('✅ Webhook successfully configured!');
    } else {
      console.error('❌ Webhook URL mismatch!');
      process.exit(1);
    }
  } catch (error) {
    console.error('❌ Error setting up webhook:', error);
    process.exit(1);
  }
}

setupWebhook();
