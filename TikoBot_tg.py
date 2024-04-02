# -*- coding: UTF-8 -*-
import logging
import PIL.Image
import configparser
from rich import print
from rich.logging import RichHandler
import google.generativeai as GoogleAI
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import filters, MessageHandler, ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

from TikoModels import Tikogpt, Tikoqwen

config = configparser.ConfigParser()
config.read("./config.ini")
# config.read("/root/TikoBot_tg/config.ini")

Bot_Token = config['Telegram']['Bot_Token']
Keys = {
    "Key_Openai": config['ChatAnywhere']['Key'], 
    "Key_Google": config['Google']['Key'], 
    "Key_Qwen"  : config['Qwen']['Key']}

openai_base = config['ChatAnywhere']['Base']
Google_Model = 'gemini-pro'
Google_Model_graph = 'gemini-pro-vision'
Init_History = [{'role': 'system', 'content': config['Others']['Init_Msg']}]
User_Allow = config['WhiteList']
Dir_images = config['Others']['Dir_images']


SETTING_safety = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE",},
        {"category": "HARM_CATEGORY_SEXUAL", "threshold": "BLOCK_NONE",},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE",},]


logging.basicConfig(
    format='%(message)s',
    level=logging.ERROR,
    handlers=[RichHandler()]
)
log = logging.getLogger("rich")

def no_permission(id):
    id = str(id)
    if len(User_Allow) == 0:
        return True
    else:
        return id not in User_Allow

def msg_logger(userID, msg, u_model, type):
    userID = str(userID)
    user = User_Allow[userID]
    log = f"[{type}]【{user}】->【{u_model}】" + msg
    print(log)

def Key_check(key):
    if len(Bot_Token) > 0:
        print("[+]Bot_Token loaded.")
    else:
        print("[!]No Bot_Token.")
        exit()
    Key_valid = False
    for key in Keys:
        if len(Keys[key]) > 8:
            print("[+]{key} loaded.")
            Key_valid = True
    if not Key_valid:
        print("[!]No Key.")
        exit()
    return 

def get_model(model):
    model_mapping = {
        "gemini-pro": model_Google,
        "gpt-3.5-turbo": model_GPT, 
        "qwen-plus": model_Qwen, 
    }
    return model_mapping.get(model.lower(), None)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "请选择文字处理模型："
    user_id = update.effective_chat.id
    if no_permission(user_id): 
        msg = "[!]No permission."
    else: 
        Key_mapping = {
            Keys["Key_Google"]: ["Gemini", 'gemini-pro'],
            Keys["Key_Openai"]: ["GPT-3.5", 'gpt-3.5-turbo'],
            Keys["Key_Qwen"]: ["通义千问", 'qwen-plus'],
        }
        keyboard = []
        for key, value in Key_mapping.items():
            if len(key) > 3:
                keyboard.append([InlineKeyboardButton(value[0], callback_data=value[1])])

        reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(msg, reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    context.user_data['model'] = query.data
    context.user_data['chatBot'] = None
    context.user_data['graphBot'] = None
    msg_logger(update.effective_chat.id, "", context.user_data['model'], "Init")
    await query.edit_message_text(text=f"{query.data}模型初始化成功。")

async def text_generator(tg_msg, model, user_msg, chat_type="Regular", chatBot=None):
    # get response
    try: 
        model_base = get_model(model)
        if chat_type == "Regular":
            response = model_base.generate_content(user_msg, stream=True)
        else:
            response = chatBot.send_message(user_msg, stream=True)
    except:
        await tg_msg.edit_text("【TikoBot】There is something wrong with the Bot,please try again.")
        return
    
    # process response
    msg_ai = ""
    len_msg_ai = 0
    for chunk in response:
        if "gemini" in model:
            msg_ai += chunk.text
        elif "gpt" in model:
            text_block = chunk.choices[0].delta
            if text_block.content is not None:
                msg_ai += text_block.content
        elif "qwen" in model:
            text_block = chunk.output.choices[0]['message']
            if text_block.content is not None:
                msg_ai = text_block.content

        if len(msg_ai) - len_msg_ai > 8:
            len_msg_ai = len(msg_ai)
            await tg_msg.edit_text(f"【{chat_type}】{model} generating...\n" + msg_ai)

    if ("gpt" in model or "qwen" in model) and chat_type == "Chat":
        chatBot.add_history("assistant", msg_ai)
    await tg_msg.edit_text(msg_ai)

async def ai_gen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    user_id = update.effective_chat.id
    if no_permission(user_id): 
        return
    elif 'chatBot' not in context.user_data:
        await context.bot.send_message(chat_id=user_id, text="请使用 /start 进行初始化")
        return
    
    chat_type = "Regular" if context.user_data['chatBot'] == None else "Chat"
    chatBot = None if chat_type == "Regular" else context.user_data['chatBot']

    msg_logger(user_id, msg, context.user_data['model'], chat_type)

    status_message = await update.message.reply_text(text=f"【{chat_type}】{context.user_data['model']} generating...")
    await text_generator(status_message, context.user_data['model'], msg, chat_type=chat_type, chatBot=chatBot)

async def ai_graph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    img_in_chat = await context.bot.get_file(update.message.photo[-1].file_id)
    user_id = update.effective_chat.id
    img_file = await img_in_chat.download_to_drive(Dir_images + str(user_id) + ".jpg")
    img = PIL.Image.open(img_file)
    msg = ""
    # print(update.message)
    if(update.message.caption is not None): 
        msg = update.message.caption
        
    if no_permission(user_id): 
        return
    elif 'graphBot' not in context.user_data:
        await context.bot.send_message(chat_id=user_id, text="请使用 /start 进行初始化")
        return 
    else:
        status_message = await update.message.reply_text(text="【Graph】Gemini-pro-vision generating...")
        msg_logger(user_id, msg, "Gemini-pro-vision", "Graph")

        msg_block = [img, msg] if len(msg) > 0 else img
        response = Gmodel_Google.generate_content(msg_block, safety_settings=SETTING_safety)
        msg_ai = response.text
    await status_message.edit_text(msg_ai)

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = ""
    try: 
        if context.user_data["chatBot"] == None and context.user_data["model"] != "gpt-4":
            msg = "【Chat】您接下来的聊天将由ai完成，再次使用 /chat 退出聊天模式。"
            model_base = get_model(context.user_data["model"])
            history_base = [] if "gemini" in context.user_data['model'] else Init_History
            context.user_data['chatBot'] = model_base.start_chat(history=history_base)
            if "gemini" in context.user_data['model']:
                context.user_data['chatBot'].send_message(Init_History[0]['content'])

        elif context.user_data["model"] == "gpt-4":
            msg = "【TikoBot】抱歉，目前 gpt-4 模型不提供连续聊天模式。"
        else: 
            msg = "【Regular】您接下来的聊天将由ai按消息逐条解析，模型将不再进行记录。"
            context.user_data['chatBot'] = None
    except:
        if not no_permission(update.effective_chat.id): 
            msg = "[!]后台更新重启，请使用 /start 命令重新初始化."
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)

async def clean(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "【TikoBot】There is no history to clean."
    if context.user_data['chatBot'] is not None:
        model_base = get_model(context.user_data['model'])
        history_base = Init_History if "gemini" not in context.user_data['model'] else []
        context.user_data['chatBot'] = model_base.start_chat(history=history_base)
        if "gemini" in context.user_data['model']:
            context.user_data['chatBot'].send_message(Init_History[0]['content'])
        msg = "【TikoBot】历史记录已清除，您可以开始一段新的聊天。"

    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")

if __name__ == '__main__':
    Key_check()

    GoogleAI.configure(api_key=Keys["Key_Google"])
    model_Google = GoogleAI.GenerativeModel(Google_Model)
    model_GPT = Tikogpt(Keys["Key_Openai"], base_url=openai_base)
    model_Qwen = Tikoqwen(Keys["Key_Qwen"], model="qwen-plus")

    Gmodel_Google = GoogleAI.GenerativeModel(Google_Model_graph)


    print("[+] Bot started.")
    application = ApplicationBuilder().token(Bot_Token).build()
    
    start_handler = CommandHandler('start', start)
    # ai_mode_handler = CommandHandler('ai', ai_mode)
    chat_handler = CommandHandler('chat', chat)
    ai_gen_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), ai_gen)
    ai_graph_handler = MessageHandler(filters.PHOTO, ai_graph)
    clean_handler = CommandHandler('clean', clean)
    unknown_handler = MessageHandler(filters.COMMAND, unknown)

    application.add_handler(start_handler)
    # application.add_handler(ai_mode_handler)
    application.add_handler(chat_handler)
    application.add_handler(ai_gen_handler)
    application.add_handler(ai_graph_handler)
    application.add_handler(clean_handler)
    application.add_handler(unknown_handler)
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling()