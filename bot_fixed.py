import nextcord
from nextcord.ext import commands
import logging
import sys
import asyncio
import re
from datetime import datetime, timedelta, timezone
from collections import Counter

# =========================
# НАСТРОЙКИ И КОНСТАНТЫ
# =========================
TOKEN = ""

WELCOME_CHANNEL_ID = 1541835086138187846
CHANNEL_TICKET = 1541859646720184391
ROLE_TO_GIVE_ID = 1541869554618204170        
CATEGORY_FOR_TICKETS_ID = 1541869430508884128 
VOICE_CHANNEL_ID = 1476666214666473630        
ROLE_TO_PING_ID = 1541873986038931596
LOG_CHANNEL_ID = 1541884925374898206

# =========================
# ЛОГИРОВАНИЕ
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("SHIZO_BOT")

# =========================
# ИНИЦИАЛИЗАЦИЯ БОТА (ОДИН РАЗ)
# =========================
intents = nextcord.Intents.all()  # Включаем все интенты для корректной работы с пользователями

bot = commands.Bot(
    command_prefix="!", 
    intents=intents,
    max_messages=None
)

# =========================
# МОДАЛЬНОЕ ОКНО АНКЕТЫ
# =========================
class ApplicationModal(nextcord.ui.Modal):
    def __init__(self):
        super().__init__(title="Анкета на вступление в семью")
        
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

        overwrites = {
            guild.default_role: nextcord.PermissionOverwrite(read_messages=False),
            interaction.user: nextcord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: nextcord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True)
        }

        ping_role = guild.get_role(ROLE_TO_PING_ID)
        if ping_role:
            overwrites[ping_role] = nextcord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel_name = f"заявка-{interaction.user.name}"
        ticket_channel = await guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)

        embed = nextcord.Embed(
            title=f"Новая заявка от {interaction.user}",
            color=nextcord.Color.blue()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="1. Ваш ник в игре", value=self.q1.value, inline=False)
        embed.add_field(name="2. Статик #", value=self.q2.value, inline=False)
        embed.add_field(name="3. Возраст OOC", value=self.q3.value, inline=False)
        embed.add_field(name="4. Цель вступления", value=self.q4.value, inline=False)
        embed.add_field(name="5. Как узнали о семье", value=self.q5.value or "Не указано", inline=False)
        embed.set_footer(text=f"ID Пользователя: {interaction.user.id}")

        mention_text = f"<@&{ROLE_TO_PING_ID}>" if ping_role else "@here"

        await ticket_channel.send(content=mention_text, embed=embed, view=TicketControlView(applicant_id=interaction.user.id))
        await interaction.followup.send(f"Ваша заявка успешно создана! Перейдите в канал: {ticket_channel.mention}", ephemeral=True)

# =========================
# КНОПКА ПОДАЧИ ЗАЯВКИ
# =========================
class StartAppView(nextcord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @nextcord.ui.button(label="Подать заявку в семью", style=nextcord.ButtonStyle.green, custom_id="start_app_btn")
    async def start_app(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_modal(ApplicationModal())

# =========================
# КНОПКИ УПРАВЛЕНИЯ ЗАЯВКОЙ
# =========================
class TicketControlView(nextcord.ui.View):
    def __init__(self, applicant_id: int):
        super().__init__(timeout=None)
        self.applicant_id = applicant_id

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        """
        Проверяет, имеет ли пользователь право управлять этой заявкой.
        Доступ разрешен Администраторам и пользователям с ролью ROLE_TO_PING_ID.
        """
        # Если пользователь администратор, разрешаем доступ
        if interaction.user.guild_permissions.administrator:
            return True
            
        # Проверяем наличие роли рекрутера/модератора по ID
        allowed_role = interaction.guild.get_role(ROLE_TO_PING_ID)
        if allowed_role and allowed_role in interaction.user.roles:
            return True
            
        # Если проверки не пройдены, отправляем скрытое сообщение и блокируем действие
        await interaction.response.send_message(
            "❌ У вас нет прав для взаимодействия с этой заявкой.", 
            ephemeral=True
        )
        return False

    @nextcord.ui.button(label="Принять", style=nextcord.ButtonStyle.green, custom_id="ticket_accept")
    async def accept(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild
        member = guild.get_member(self.applicant_id)
        role = guild.get_role(ROLE_TO_GIVE_ID)
        log_channel = guild.get_channel(LOG_CHANNEL_ID)

        if member and role:
            try:
                await member.add_roles(role)
                await interaction.channel.send(f"🎉 {member.mention} был успешно принят в семью и получил роль {role.name}!")
                await member.send(f"✨ Поздравляем! Ваша заявка в семью на сервере **{guild.name}** одобрена модератором {interaction.user}. Вам выдана роль **{role.name}**.")
            except nextcord.Forbidden:
                await interaction.channel.send("⚠️ Бот не смог отправить сообщение в ЛС пользователю (закрыта личка).")
            except Exception as e:
                logger.error(f"Ошибка при выдаче роли: {e}")
        else:
            await interaction.channel.send("⚠️ Не удалось выдать роль (пользователь покинул сервер или роль удалена).")

        if log_channel and interaction.message.embeds:
            log_embed = nextcord.Embed(title="🟢 Заявка Одобрена", color=nextcord.Color.green())
            log_embed.add_field(name="Кандидат:", value=f"{member.mention if member else 'Пользователь вышел'} (`{self.applicant_id}`)", inline=True)
            log_embed.add_field(name="Модератор:", value=f"{interaction.user.mention}", inline=True)

            source_embed = interaction.message.embeds[0]
            for field in source_embed.fields:
                log_embed.add_field(name=field.name, value=field.value or "Не указано", inline=False)

            await log_channel.send(embed=log_embed)

        # Сначала редактируем интерфейс, отключая кнопки
        message = interaction.message
        embed = message.embeds[0]
        embed.color = nextcord.Color.green()
        embed.title = "🟢 ЗАЯВКА ОДОБРЕНА"
        
        for item in self.children:
            item.disabled = True
            
        await message.edit(embed=embed, view=self)
        await interaction.channel.send("🟢 Заявка одобрена. Этот канал будет удален через 5 секунд...")

        # Задержка перед удалением канала, чтобы Discord успел обновить API сообщения
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete()
        except nextcord.NotFound:
            pass

    @nextcord.ui.button(label="Отклонить", style=nextcord.ButtonStyle.red, custom_id="ticket_reject")
    async def reject(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild
        member = guild.get_member(self.applicant_id)
        log_channel = guild.get_channel(LOG_CHANNEL_ID)
        
        if member:
            try:
                await member.send(f"❌ К сожалению, ваша заявка в семью на сервере **{guild.name}** была отклонена модератором {interaction.user}.")
            except nextcord.Forbidden:
                await interaction.channel.send("⚠️ Бот не смог отправить сообщение в ЛС пользователю (закрыта личка).")
                
        if log_channel and interaction.message.embeds:
            log_embed = nextcord.Embed(title="🔴 Заявка Отклонена", color=nextcord.Color.red())
            log_embed.add_field(name="Кандидат:", value=f"{member.mention if member else 'Пользователь вышел'} (`{self.applicant_id}`)", inline=True)
            log_embed.add_field(name="Модератор:", value=f"{interaction.user.mention}", inline=True)

            source_embed = interaction.message.embeds[0]
            for field in source_embed.fields:
                log_embed.add_field(name=field.name, value=field.value or "Не указано", inline=False)

            await log_channel.send(embed=log_embed)
            
        message = interaction.message
        embed = message.embeds[0]
        embed.color = nextcord.Color.red()
        embed.title = "🔴 ЗАЯВКА ОТКЛОНЕНА"
        
        for item in self.children:
            item.disabled = True
            
        await message.edit(embed=embed, view=self)
        await interaction.channel.send("⛔ Заявка отклонена. Этот канал будет удален через 5 секунд...")
        
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete()
        except nextcord.NotFound:
            pass

    @nextcord.ui.button(label="Вызвать на обзвон", style=nextcord.ButtonStyle.blurple, custom_id="ticket_call")
    async def call(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild
        member = guild.get_member(self.applicant_id)
        voice_channel = guild.get_channel(VOICE_CHANNEL_ID)

        if member:
            voice_mention = voice_channel.mention if voice_channel else "голосовой канал"
            await interaction.channel.send(
                f"📞 {member.mention}, вас вызывает на обзвон администратор {interaction.user.mention}!"
                f"Пожалуйста, зайдите в {voice_mention}."
            )
        else:
            await interaction.channel.send("⚠️ Пользователь не найден на сервере.")

# =========================
# СЛЭШ-КОМАНДЫ И ДИРЕКТИВЫ
# =========================
@bot.slash_command(name="rectop", description="Показывает топ рекрутов за последние 7 дней")
@commands.has_permissions(administrator=True)
async def rectop(interaction: nextcord.Interaction):
    await interaction.response.defer()
    guild = interaction.guild
    log_channel = guild.get_channel(LOG_CHANNEL_ID)
    if not log_channel:
        await interaction.followup.send("❌ Канал логов заявок не найден.", ephemeral=True)
        return

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    recruiter_counts = Counter()

    async for message in log_channel.history(limit=None, after=week_ago, before=now):
        if not message.embeds:
            continue
        embed = message.embeds[0]
        if embed.title != "🟢 Заявка Одобрена":
            continue
        for field in embed.fields:
            if field.name == "Модератор:":
                match = re.search(r"<@!?(\d+)>", field.value or "")
                if match:
                    recruiter_counts[int(match.group(1))] += 1
                break

    embed = nextcord.Embed(title="Топ рекрутов за неделю", color=nextcord.Color.blue(), timestamp=now)
    if not recruiter_counts:
        embed.description = "За последние 7 дней одобренных заявок не было."
    else:
        lines = []
        for position, (moderator_id, count) in enumerate(recruiter_counts.most_common(), 1):
            member = guild.get_member(moderator_id)
            name = member.mention if member else f"<@{moderator_id}>"
            medal = "🥇" if position == 1 else "🥈" if position == 2 else "🥉" if position == 3 else f"**{position}.**"
            word = "заявка" if count == 1 else "заявки" if 2 <= count <= 4 else "заявок"
            lines.append(f"{medal} {name} — **{count} {word}**")
        embed.description = "
".join(lines)
    embed.set_footer(text="Статистика за последние 7 дней")
    await interaction.followup.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    maroon_color = nextcord.Color.from_rgb(128, 0, 32)
    embed = nextcord.Embed(
        description="**Вступай в нашу семью!**\nЗаполни форму чтобы стать частью семьи",
        color=maroon_color
    )
    embed.set_image(url="https://cdn.discordapp.com/attachments/1476666214666473629/1541870399233458176/r017w6g62r0ku20i.png") 

    await ctx.send(embed=embed, view=StartAppView())
    try:
        await ctx.message.delete()
    except nextcord.NotFound:
        pass

# =========================
# ЕДИНЫЙ ОБРАБОТЧИК ON_READY
# =========================
@bot.event
async def on_ready():
    logger.info("========================================")
    logger.info("БОТ УСПЕШНО ЗАПУЩЕН")
    logger.info(f"Имя бота: {bot.user}")
    logger.info(f"ID бота: {bot.user.id}")
    logger.info(f"Серверов: {len(bot.guilds)}")
    logger.info("========================================")
    
    # Регистрируем View для персистентности (чтобы кнопки работали после перезагрузки)
    bot.add_view(StartAppView())
    
@bot.event
async def on_member_join(member: nextcord.Member):

    logger.info("========================================")
    logger.info("СРАБОТАЛО СОБЫТИЕ on_member_join")
    logger.info(f"Пользователь: {member}")
    logger.info(f"Имя: {member.name}")
    logger.info(f"ID пользователя: {member.id}")
    logger.info(f"Сервер: {member.guild.name}")
    logger.info(f"ID сервера: {member.guild.id}")
    logger.info("========================================")

    # Получаем канал
    logger.info(
        f"Ищу канал с ID: {WELCOME_CHANNEL_ID}"
    )

    channel = member.guild.get_channel(
        WELCOME_CHANNEL_ID
    )

    # Канал не найден
    if channel is None:

        logger.error(
            "❌ КАНАЛ НЕ НАЙДЕН!"
        )

        logger.error(
            f"Проверь WELCOME_CHANNEL_ID: "
            f"{WELCOME_CHANNEL_ID}"
        )

        return

    logger.info(
        f"✅ Канал найден: #{channel.name}"
    )

    # =========================
    # СОЗДАЁМ EMBED
    # =========================

    embed = nextcord.Embed(
        title="Добро пожаловать на server SHIZO family",

        description=(
            f"{member.mention}, чтобы подать заявку "
            f"в нашу семью зайди в канал "
            f"<#1541859646720184391>"
        ),

        color=0x800000
    )

    logger.info(
        "Embed создан"
    )

    # =========================
    # ОТПРАВКА
    # =========================

    try:

        logger.info(
            f"Пытаюсь отправить Embed "
            f"в #{channel.name}"
        )

        message = await channel.send(
            embed=embed
        )

        logger.info(
            f"✅ EMBED ОТПРАВЛЕН!"
        )

        logger.info(
            f"ID сообщения: {message.id}"
        )

    except nextcord.Forbidden:

        logger.error(
            "❌ Discord запретил отправку сообщения!"
        )

        logger.error(
            "Проверь права Send Messages и Embed Links."
        )

    except nextcord.HTTPException as error:

        logger.error(
            f"❌ Ошибка Discord API: {error}"
        )

    except Exception as error:

        logger.exception(
            f"❌ НЕИЗВЕСТНАЯ ОШИБКА: {error}"
        )

# =========================
# ЗАПУСК БОТА
# =========================
logger.info("Запускаю бота...")
try:
    bot.run(TOKEN)
except Exception as error:
    logger.exception(f"❌ БОТ НЕ ЗАПУСТИЛСЯ: {error}")
