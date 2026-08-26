import nextcord
from nextcord.ext import commands
import logging
import sys

# =========================
# НАСТРОЙКИ
# =========================
bot = commands.Bot(
    command_prefix="!", 
    intents=nextcord.Intents.all(),
    max_messages=None # Бот перестанет помнить старые сообщения, освободив ОЗУ
)

TOKEN = "MTU0MTc4NTU4ODAxNTgzMzExMA.GG-6Do.P0b2ql89jwO7c28ynawwuJ1vmZ_l0nPaN4rHBI"

# ID канала, куда отправлять приветственный Embed
WELCOME_CHANNEL_ID = 1541835086138187846

CHANNEL_TICKET = 1541859646720184391


# =========================
# ЛОГИ
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            "bot.log",
            encoding="utf-8"
        )
    ]
)

logger = logging.getLogger("SHIZO_BOT")


# =========================
# INTENTS
# =========================

intents = nextcord.Intents.default()

# Обязательно для on_member_join
intents.members = True


# =========================
# BOT
# =========================

bot = commands.Bot(
    intents=intents
)


# =========================
# ЗАПУСК БОТА
# =========================

@bot.event
async def on_ready():

    logger.info("========================================")
    logger.info("БОТ УСПЕШНО ЗАПУЩЕН")
    logger.info(f"Имя бота: {bot.user}")
    logger.info(f"ID бота: {bot.user.id}")
    logger.info(f"Серверов: {len(bot.guilds)}")

    for guild in bot.guilds:
        logger.info(
            f"Сервер: {guild.name} | ID: {guild.id}"
        )

    logger.info("========================================")

ROLE_TO_GIVE_ID = 1541869554618204170        # ID роли, которую выдают при принятии
CATEGORY_FOR_TICKETS_ID = 1541869430508884128 # ID категории, где будут создаваться каналы-заявки
VOICE_CHANNEL_ID = 1476666214666473630        # ID голосового канала для обзвона
ROLE_TO_PING_ID = 1541873986038931596
LOG_CHANNEL_ID = 1541884925374898206

bot = commands.Bot(command_prefix="!", intents=nextcord.Intents.all())

# --- 2. МОДАЛЬНОЕ ОКНО (ФОРМА ИЗ 5 ВОПРОСОВ) ---
class ApplicationModal(nextcord.ui.Modal):
    def __init__(self):
        super().__init__(title="Анкета на вступление в семью")
        
        # 5 полей для ввода
        self.q1 = nextcord.ui.TextInput(label="Ваш ник в игре", placeholder="Ryan Shizo", min_length=2, max_length=50, required=True)
        self.q2 = nextcord.ui.TextInput(label="Статик #", placeholder="#249644", min_length=3, max_length=50, required=True)
        self.q3 = nextcord.ui.TextInput(label="Возраст OOC", placeholder="Сколько вам лет", min_length=1, max_length=20, required=True)
        self.q4 = nextcord.ui.TextInput(label="Цель вступления", placeholder="", style=nextcord.TextInputStyle.paragraph, required=True)
        self.q5 = nextcord.ui.TextInput(label="Как узнали о семье", placeholder="", style=nextcord.TextInputStyle.paragraph, required=False)
        
        self.add_item(self.q1)
        self.add_item(self.q2)
        self.add_item(self.q3)
        self.add_item(self.q4)
        self.add_item(self.q5)
        

    async def callback(self, interaction: nextcord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        category = guild.get_channel(CATEGORY_FOR_TICKETS_ID)
        
        if not category or not isinstance(category, nextcord.CategoryChannel):
            await interaction.followup.send("Ошибка: Категория для заявок не найдена. Обратитесь к администратору.", ephemeral=True)
            return

        # Настройка прав для нового канала (видит создатель и модераторы)
        overwrites = {
            guild.default_role: nextcord.PermissionOverwrite(read_messages=False),
            interaction.user: nextcord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: nextcord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True)
        }

        ping_role = guild.get_role(ROLE_TO_PING_ID)
        if ping_role:
            overwrites[ping_role] = nextcord.PermissionOverwrite(read_messages=True, send_messages=True)

        # Создание канала заявки с именем пользователя
        channel_name = f"заявка-{interaction.user.name}"
        ticket_channel = await guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)

        # Сборка синего эмбеда с ответами
        embed = nextcord.Embed(
            title=f"Новая заявка от {interaction.user}",
            color=nextcord.Color.blue() # Синий цвет
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="1. Ваш ник в игре", value=self.q1.value, inline=False)
        embed.add_field(name="2. Статик #", value=self.q2.value, inline=False)
        embed.add_field(name="3. Возраст OOC", value=self.q3.value, inline=False)
        embed.add_field(name="4. Цель вступления", value=self.q4.value, inline=False)
        embed.add_field(name="5. Как узнали о семье", value=self.q5.value or "Не указано", inline=False)
        embed.set_footer(text=f"ID Пользователя: {interaction.user.id}")

        mention_text = f"<@&{ROLE_TO_PING_ID}>" if ping_role else "@here"

        # Отправляем эмбед с кнопками управления в созданный канал
        await ticket_channel.send(content=mention_text, embed=embed, view=TicketControlView(applicant_id=interaction.user.id))
        await interaction.followup.send(f"Ваша заявка успешно создана! Перейдите в канал: {ticket_channel.mention}", ephemeral=True)

# --- 1. КНОПКА ПОДАЧИ ЗАЯВКИ (ГЛАВНОЕ МЕНЮ) ---
class StartAppView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # Бессрочная кнопка

    @nextcord.ui.button(label="Подать заявку в семью", style=nextcord.ButtonStyle.green, custom_id="start_app_btn")
    async def start_app(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        # При нажатии открываем модальное окно
        await interaction.response.send_modal(ApplicationModal())

# --- 3. КНОПКИ УПРАВЛЕНИЯ ВНУТРИ ЗАЯВКИ ---
class TicketControlView(nextcord.ui.View):
    def __init__(self, applicant_id: int):
        super().__init__(timeout=None)
        self.applicant_id = applicant_id

    @nextcord.ui.button(label="Принять", style=nextcord.ButtonStyle.green)
    async def accept(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild
        member = guild.get_member(self.applicant_id)
        role = guild.get_role(ROLE_TO_GIVE_ID)
        log_channel = guild.get_channel(LOG_CHANNEL_ID)

        # Выдаем роль, если пользователь еще на сервере
        if member and role:
            await member.add_roles(role)
            await interaction.channel.send(f"🎉 {member.mention} был успешно принят в семью и получил роль {role.name}!")
            
            try:
                await member.send(f"✨ Поздравляем! Ваша заявка в семью на сервере **{guild.name}** была одобрена модератором {interaction.user}. Вам выдана роль **{role.name}**.")
            except nextcord.Forbidden:
                await interaction.channel.send("⚠️ Бот не смог отправить сообщение в ЛС пользователю (у него закрыты личные сообщения).")
        else:
            await interaction.channel.send("⚠️ Не удалось выдать роль (пользователь покинул сервер или роль удалена).")

        if log_channel:
            log_embed = nextcord.Embed(title="🟢 Заявка Одобрена", color=nextcord.Color.green())
            log_embed.add_field(name="Кандидат:", value=f"{member.mention if member else 'Пользователь вышел'} (`{self.applicant_id}`)", inline=True)
            log_embed.add_field(name="Модератор:", value=f"{interaction.user.mention}", inline=True)

            # Переносим ВСЕ пункты заявки из исходного эмбеда в лог.
            source_embed = interaction.message.embeds[0]
            for field in source_embed.fields:
                log_embed.add_field(name=field.name, value=field.value or "Не указано", inline=False)

            await log_channel.send(embed=log_embed)


        # Меняем цвет эмбеда на зеленый и отключаем кнопки
        message = interaction.message
        embed = message.embeds[0]
        embed.color = nextcord.Color.green()
        embed.title = "🟢 ЗАЯВКА ОДОБРЕНА"
        
        for item in self.children:
            item.disabled = True
            
        await message.edit(embed=embed, view=self)

        await message.edit(embed=embed, view=self)
        await interaction.channel.send("🟢 Заявка одобрена. Этот канал будет удален через 5 секунд...")


        import asyncio
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @nextcord.ui.button(label="Отклонить", style=nextcord.ButtonStyle.red)
    async def reject(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild
        member = guild.get_member(self.applicant_id)
        log_channel = guild.get_channel(LOG_CHANNEL_ID)
        
        if member:
            try:
                await member.send(f"❌ К сожалению, ваша заявка в семью на сервере **{guild.name}** была отклонена модератором {interaction.user}.")
            except nextcord.Forbidden:
                await interaction.channel.send("⚠️ Бот не смог отправить сообщение в ЛС пользователю (у него закрыты личные сообщения).")
                
        if log_channel:
            log_embed = nextcord.Embed(title="🔴 Заявка Отклонена", color=nextcord.Color.red())
            log_embed.add_field(name="Кандидат:", value=f"{member.mention if member else 'Пользователь вышел'} (`{self.applicant_id}`)", inline=True)
            log_embed.add_field(name="Модератор:", value=f"{interaction.user.mention}", inline=True)

            # Берем все ответы из исходного эмбеда заявки.
            # self.q1/self.q2/... здесь недоступны, потому что они принадлежат ApplicationModal.
            source_embed = interaction.message.embeds[0]
            for field in source_embed.fields:
                log_embed.add_field(name=field.name, value=field.value or "Не указано", inline=False)

            await log_channel.send(embed=log_embed)
            
            
        # Меняем цвет эмбеда на красный
        message = interaction.message
        embed = message.embeds[0]
        embed.color = nextcord.Color.red()
        embed.title = "🔴 ЗАЯВКА ОТКЛОНЕНА"
        
        for item in self.children:
            item.disabled = True
            
        await message.edit(embed=embed, view=self)
        await interaction.channel.send("⛔ Заявка отклонена. Этот канал будет удален через 5 секунд...")
        
        # Удаляем канал через 5 секунд
        import asyncio
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @nextcord.ui.button(label="Вызвать на обзвон", style=nextcord.ButtonStyle.blurple)
    async def call(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild
        member = guild.get_member(self.applicant_id)
        voice_channel = guild.get_channel(VOICE_CHANNEL_ID)

        if member:
            voice_mention = voice_channel.mention if voice_channel else "голосовой канал"
            # Тегаем человека и приглашаем на обзвон
            await interaction.channel.send(
                f"📞 {member.mention}, вас вызывает на обзвон администратор {interaction.user.mention}!\n"
                f"Пожалуйста, зайдите в {voice_mention}."
            )
        else:
            await interaction.channel.send("⚠️ Пользователь не найден на сервере.")

# --- 4. КОМАНДА ДЛЯ СОЗДАНИЯ СТАРТОВОГО ЭМБЕДА ---
@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    # Бордовый цвет (Hex: #800020 в десятичной системе: 8388640)
    maroon_color = nextcord.Color.from_rgb(128, 0, 32)
    
    embed = nextcord.Embed(
        description="**Вступай в нашу семью!**\nЗаполни форму чтобы стать частью семьи",
        color=maroon_color
    )
    # Сюда вставьте прямую ссылку на картинку (png/jpg)
    embed.set_image(url="https://cdn.discordapp.com/attachments/1476666214666473629/1541870399233458176/r017w6g62r0ku20i.png?ex=6a8f2a35&is=6a8dd8b5&hm=5fdc0546df619c97d824235424da9ad8cc37b6bdd354d387e98177d050427b68&") 

    await ctx.send(embed=embed, view=StartAppView())
    await ctx.message.delete() # Удаляем исходную команду администратора для красоты

@bot.event
async def on_ready():
    print(f"Робот {bot.user} запущен и готов к работе!")


# =========================
# ЗАПУСК
# =========================

logger.info("Запускаю бота...")

try:

    bot.run(TOKEN)

except Exception as error:

    logger.exception(
        f"❌ БОТ НЕ ЗАПУСТИЛСЯ: {error}"
    )
