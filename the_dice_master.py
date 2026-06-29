# LIBRARIES =====================================================
# Discord Libraries
import discord
from discord.ext import commands
from discord import app_commands

# Other Libraries
import configparser
import os
import glob
import json
import sqlite3
from pathlib import Path
from os import listdir

# ===============================================================

# CONFIGURATIONS ===============================================================================================================
# Configparser --------------------------------------------------
config = configparser.ConfigParser()  # init
config.read("config.ini")  # Definition of the configuration file

# Bot Class
class DiceMasterBot(commands.Bot):
    """
    Custom Discord bot implementation for the Dice Master system.

    This subclass extends commands.Bot to enforce architectural discipline,
    proper dependency injection, and correct asynchronous lifecycle management.

    Justification for Subclassing:
    ------------------------------
    A custom subclass is strictly mandatory due to two architectural requirements:

    1. State and Dependency Injection: 
       By overriding the constructor (__init__), the class securely binds an external 
       configuration object (bot_config) to self.config at instantiation time. This 
       guarantees that vital parameters (such as 'DM_ID') are available in memory before any peripheral module is initialized, preventing runtime AttributeError anomalies 
       within Cog constructors.

    2. Asynchronous Lifecycle Orchestration:
       By overriding setup_hook(), the bot gains an isolated, single-execution asynchronous 
       window to load extensions via self.load_extension() before the WebSocket connection 
       to the Discord gateway is established. This effectively prevents the dangerous 
       anti-pattern of loading extensions inside on_ready(), which is highly volatile and 
       subject to recurrent triggers during gateway reconnections.
    """
    def __init__(self, command_prefix, intents, bot_config):
        super().__init__(command_prefix=command_prefix, intents=intents)
        self.config = bot_config


    async def setup_hook(self):
        """
        Load extensions strictly inside the setup_hook, NEVER in on_ready.
        """
        extensions = [
            'cogs.battle',
            'cogs.deterministic_mock',
            'cogs.other_tests',
            'cogs.skill_test'
        ]
        
        for extension in extensions:
            try:
                await self.load_extension(extension)
                print(f'Successfully loaded: {extension}')
            except Exception as e:
                print(f'Failed to load {extension}: {e}')

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')

# Definition of permissions
intents = discord.Intents.default()
intents.message_content = True
bot = DiceMasterBot(command_prefix=config["BOT"]["Prefix"], intents=intents, bot_config=config)  # The config['BOT']['Prefix'] defines the bot command prefix

# INIT SQL DATABASE ==============================================
def initialize_system_database() -> None:
    """
    Validates the existence of the SQLite binary file. If absent, it constructs
    the database dynamically by reading and executing the DDL instructions 
    from the initialization script.
    """
    # Defining the structural paths using the modern pathlib module
    base_directory = Path("data")
    binary_db_path = base_directory / "database.db"
    sql_schema_path = base_directory / "init.sql"

    # Step 1: Guarantee the directory topology exists before any file operation
    base_directory.mkdir(parents=True, exist_ok=True)

    # Step 2: Validate the existence of the binary database file
    if not binary_db_path.exists():
        
        # It is a fatal architectural error if the schema script is also missing
        if not sql_schema_path.exists():
            raise FileNotFoundError(
                f"Initialization aborted: The required DDL script '{sql_schema_path}' "
                "is missing from the filesystem."
            )
        
        # Step 3: Read the schema instructions and instantiate the database
        with open(sql_schema_path, 'r', encoding='utf-8') as schema_file:
            schema_instructions = schema_file.read()

        with sqlite3.connect(binary_db_path) as connection:
            cursor = connection.cursor()
            cursor.executescript(schema_instructions)
            connection.commit()

# NORMAL COMMANDS ==================================================
# Sync command 
@bot.command(name="sync")
@commands.is_owner()  # Ensures that only the bot owner can run this command
async def sync(ctx):
    try:
        syncs = await bot.tree.sync()
        await ctx.reply(f"{len(syncs)} Commands successfully synchronized")

    except Exception as e:
        await ctx.reply(f"Commands not synchronized {e}")


# SLASH COMMANDS ===============================================================================================================

# Sheet -----------------------------------------------------------
def build_character_embed(sheet: dict) -> discord.Embed:

    # SHEET DATA EXCRATION
    # name
    name = sheet_data_extractor(sheet, ['name']) or 'No Name'

    #race
    race = sheet_data_extractor(sheet, ["race"]) or 'No Race'

    # Base Stats
    st = sheet_data_extractor(sheet, ["base_stats", "st"]) or 10
    dx = sheet_data_extractor(sheet, ["base_stats", "dx"]) or 10
    iq = sheet_data_extractor(sheet, ["base_stats", "iq"]) or 10
    ht = sheet_data_extractor(sheet, ["base_stats", "ht"]) or 10

    # Secondary Stats
    additional_hp = sheet_data_extractor(sheet, ["secondary_stats", "additional_hp"]) or 0
    additional_will = sheet_data_extractor(sheet, ["secondary_stats", "additional_will"]) or 0
    additional_per = sheet_data_extractor(sheet, ["secondary_stats", "additional_per"]) or 0
    additional_fp = sheet_data_extractor(sheet, ["secondary_stats", "additional_fp"]) or 0
    additional_basic_speed = sheet_data_extractor(sheet, ["secondary_stats", "additional_basic_speed"]) or 0
    additional_basic_move = sheet_data_extractor(sheet, ["secondary_stats", "additional_basic_move"]) or 0

    # Additional Stats
    additional_stats = sheet_data_extractor(sheet, ["additional_stats"]) or {}
    additional_stats_text = ""
    # -- This block iterates through the dictionary, collecting all data and adding it formatted to the string.
    for stat_name, stat_value in additional_stats.items():
        # Validates if the key has a name to prevent empty placeholders like "": 0 from being displayed.
        if stat_name:
            additional_stats_text += f">>> {stat_name}: {stat_value}\n"

    # Physical Constitution
    body_type = sheet_data_extractor(sheet, ["physical_constitution", "body_type"]) or "Normal"
    sm_modifier = sheet_data_extractor(sheet, ["physical_constitution", "size_modifier", "modifier"]) or 0
    gigantism = sheet_data_extractor(sheet, ["physical_constitution", "size_modifier", "gigantism"]) or False
    dwarfism = sheet_data_extractor(sheet, ["physical_constitution", "size_modifier", "dwarfism"]) or False

    # Age and Beauty
    age = sheet_data_extractor(sheet, ["age_and_beauty", "age"]) or "Adulto"
    appearance = sheet_data_extractor(sheet, ["age_and_beauty", "appearance", "lv_appearance"]) or "Comum"

    other_options = sheet_data_extractor(sheet, ["age_and_beauty", "appearance", "other_opitions"]) or {} # Collect the entire dictionary.
    other_options_text = "" # Creates a string with all the data from other options.
    for option, value in other_options.items():
        if option: 
            other_options_text += f"{option}: {value}\n"

    # Social Background
    low_nt = sheet_data_extractor(sheet, ["social_background", "nt", "low_nt"]) or False
    high_nt = sheet_data_extractor(sheet, ["social_background", "nt", "high_nt"]) or False
    
    cultures = sheet_data_extractor(sheet, ["social_background", "cultures"]) or [] # Collect the entire list.
    cultures_text = ""
    for culture in cultures:
        cultures_text += f"{culture}\n"
    
    languages = sheet_data_extractor(sheet, ["social_background", "languages"]) or {} # Collect the entire dictionary.
    languages_text = ""
    # -- This block iterates through the dictionary, collecting all data and adding it formatted to the string created above.
    for lang_name, levels in languages.items():
        if lang_name:
            spoken = levels.get("Spoken_level", "None")
            written = levels.get("Written_level", "None")
            languages_text += f"{lang_name} — Fala: {spoken} ┃ Escrita: {written}\n"

    # Wealth and influence
    wealth_level = sheet_data_extractor(sheet, ["wealth_and_influence", "wealth_level"]) or "Médio"

    reputations = sheet_data_extractor(sheet, ["wealth_and_influence", "reputation"]) or {} # Collect the entire dictionary.
    reputation_text = ""
    # -- This block iterates through the dictionary, collecting all data and adding it formatted to the string created above.
    for rep_name, rep_info in reputations.items():
        if rep_name:  
            details = rep_info.get("details", "Sem detalhes.")
            modifier = rep_info.get("reaction_test_modifier", 0)
            people = rep_info.get("people affected", "Não especificado")
            frequency = rep_info.get("recognition_frequency", "Não especificado")
            # Format the modifier sign (+ or -) for GURPS notation
            mod_sign = f"+{modifier}" if modifier >= 0 else f"{modifier}"
            reputation_text += (
                f"__{rep_name}__\n"
                f"Modificadir de Reação: {mod_sign}\n"
                f"Afeta: {people}\n"
                f"Reconhecido: {frequency}\n"
                f"Detalhes: {details}\n\n"
            )

    social_status = sheet_data_extractor(sheet, ["wealth_and_influence", "importance", "social_status"]) or {}
    social_status_text = ""
    # -- This block iterates through the dictionary, collecting all data and adding it formatted to the string created above.
    for social_status_name, social_status_level in social_status.items():
        if social_status_name:  
            social_status_text += f"{social_status_name}: {social_status_level}\n"
    
    hierarchies = sheet_data_extractor(sheet, ["wealth_and_influence", "importance", "hierarchy"]) or {} # Collect the entire dictionary.
    hierarchy_text = ""
    # -- This block iterates through the dictionary, collecting all data and adding it formatted to the string created above.
    for rank_name, rank_level in hierarchies.items():
        if rank_name:  
            hierarchy_text += f"{rank_name}: {rank_level}\n"


    # Advantages
    advantages = sheet_data_extractor(sheet, ["advantages"]) or {} # Collect the entire dictionary.
    advantages_text = ""
    # -- This block iterates through the dictionary, collecting all data and adding it formatted to the string created above.
    for advantage_name, advantage_page in advantages.items():
        if advantage_name:
            advantage_page_item = advantage_page.get("page", "?")
            advantages_text += f"{advantage_name} (Page: {advantage_page_item})\n"

    # Disadvantages
    disadvantages = sheet_data_extractor(sheet, ["disadvantages"]) or {} # Collect the entire dictionary.
    disadvantages_text = ""
    # -- This block iterates through the dictionary, collecting all data and adding it formatted to the string created above.
    for disadvantage_name, disadvantage_page in disadvantages.items():
        if disadvantage_name:
            disadvantage_page_item = disadvantage_page.get("page", "?")
            disadvantages_text += f"{disadvantage_name} (Page: {disadvantage_page_item})\n"

    # Skills 
    # -- 
    skills = sheet_data_extractor(sheet, ["skills"]) or {} # Collect the entire dictionary.
    skills_text = ""
    # -- This block iterates through the dictionary, collecting all data and adding it formatted to the string created above.
    for skill_name, skill_info in skills.items():
        if skill_name:
            dominant_stat = skill_info.get("dominant_stat", "?")
            
            # This block stores the value of the skill's dominant stat into a variable.
            if dominant_stat =='ST':
                dominant_stat_for_text = st
            elif dominant_stat == 'DX':
                dominant_stat_for_text = dx
            elif dominant_stat == 'IQ':
                dominant_stat_for_text = iq
            elif dominant_stat == "HT":
                dominant_stat_for_text = ht
            else:
                dominant_stat_for_text = 0


            difficulty = skill_info.get("difficulty", "?")
            level = skill_info.get("level", 0)
            page = skill_info.get("page", "?")
            # Format the level modifier sign (+ or -) for GURPS notation
            level_sign = f"+{level}" if level >= 0 else f"{level}"
            page_text = f" [p. {page}]" if page else ""

            if dominant_stat_for_text == 0:
                level_text = "?"
            else:
                level_text = dominant_stat_for_text + level

            skills_text += (
                f"**{skill_name}**\n"
                f"Atributo Dominante: {dominant_stat}\n"
                f"Dificuldade: {difficulty}\n"
                f"Nível: {level_text} ({level_sign})\n"
                f"Página: {page_text}\n\n"
            )
    
    # Magias
    magias = sheet_data_extractor(sheet, ["magias"]) or {} # Collect the entire dictionary.
    magias_text = ""
    # -- This block iterates through the dictionary, collecting all data and adding it formatted to the string created above.
    for magia_name, magia_info in magias.items():
        if magia_name:
            dominant_stat = magia_info.get("dominant_stat", "?")

            # This block stores the value of the skill's dominant stat into a variable.
            if dominant_stat =='ST':
                dominant_stat_for_text = st
            elif dominant_stat == 'DX':
                dominant_stat_for_text = dx
            elif dominant_stat == 'IQ':
                dominant_stat_for_text = iq
            elif dominant_stat == "HT":
                dominant_stat_for_text = ht
            else:
                dominant_stat_for_text = 0

            difficulty = magia_info.get("difficulty", "?")
            level = magia_info.get("level", 0)
            cost = magia_info.get("cost", 0)
            page = magia_info.get("page", "?")
            # Format the level modifier sign (+ or -) for GURPS notation
            level_sign = f"+{level}" if level >= 0 else f"{level}"
            page_text = f" [p. {page}]" if page else ""

            if dominant_stat_for_text == 0:
                level_text = "?"
            else:
                level_text = dominant_stat_for_text + level

            magias_text += (
                f"**{magia_name}**\n"
                f"Atributo Dominante: {dominant_stat}\n"
                f"Dificuldade: {difficulty}\n"
                f"Nível: {level_text} ({level_sign})\n"
                f"Custo: {cost}\n"
                f"Página: {page_text}\n\n"
            )
    
    
    # ---- Embed ----
    character_embed = discord.Embed(
        title= f"{name.upper()}",
        color = discord.Color.dark_purple()
    )
    # Race
    character_embed.add_field(
        name="Raça",
        value=race,
        inline=False
    )
    # Base Stats
    character_embed.add_field(
        name="Atributos Básicos",
        value=f">>> ST: {st}\nDX: {dx}\nIQ: {iq}\nHT: {ht}",
        inline= False
    )
    # Secondary Stats
    character_embed.add_field(
        name="Características Secundárias",
        value= (
            f" >>> PV Máximo: {st + additional_hp}\n"
            f"Vontade: {iq + additional_will}\n"
            f"Percepção: {iq + additional_per}\n"
            f"PF: {ht + additional_fp}\n"
            f"Velocidade Básica: {((ht + dx)/4) + additional_basic_speed}\n"
            f"Deslocamento Básico (Sem Carga): {int(((ht + dx)/4) + additional_basic_speed) + additional_basic_move}"
        ),
        inline=False
    )
    # Additional Stats
    character_embed.add_field(
        name="Características Adicionais",
        value=additional_stats_text,
        inline=False
    )
    # Physical Constitution
    physical_constitution_text = (
        f"Tipo de Corpo: {body_type}\n"
        f"Modificador de Tamanho: {sm_modifier}"
    )
    if gigantism:
        physical_constitution_text += "\nGigantismo: Sim"
    elif dwarfism:
        physical_constitution_text += "\nNanismo: Sim"

    character_embed.add_field(
        name= "Constituição Física",
        value= f">>> {physical_constitution_text}",
        inline=False
    )
    # Age and Beauty
    character_embed.add_field(
        name="Idade e Beleza",
        value=(
            f" >>> Idade: {age}\n"
            f"Aparência: {appearance}\n"
            f"\n**Otras Opções**\n{other_options_text}"
        ),
        inline=False
    )
    # Social Background
    social_background_text = ""
    if low_nt:
        social_background_text += "NT Baixo: Verdadeiro\n"
    elif high_nt:
        social_background_text += "NT Elevado: Verdadeiro\n"
    
    social_background_text += f"**Culturas**\n{cultures_text}"
    social_background_text += f"**\nLínguas**\n{languages_text}"

    character_embed.add_field(
        name="Antecedentes Sociais",
        value= f" >>> {social_background_text}",
        inline=False
    )
    # Wealth and influence
    wealth_and_influence_text = f"Nível de Riqueza: {wealth_level}\n"
    wealth_and_influence_text += f"\n**Status Social**\n {social_status_text}"
    wealth_and_influence_text += f"\n**Hierarquias**\n{hierarchy_text}"
    wealth_and_influence_text += f"\n**Reputações**\n{reputation_text}"

    if len(wealth_and_influence_text) > 1000:
        wealth_and_influence_text = wealth_and_influence_text[:950] + "...\n\nMais texto do que é permitido enviar..."

    character_embed.add_field(
        name="Riqueza e Influência",
        value=f" >>> {wealth_and_influence_text}",
        inline=False
    )

    # Advantages
    if len(advantages_text) > 1000:
        advantages_text = advantages_text[:950] + "...\n\nMais texto do que é permitido enviar..."

    character_embed.add_field(
        name="Vantagens",
        value=f">>> {advantages_text}",
        inline=False
    )

    # Disadvantages
    if len(disadvantages_text) > 1000:
        disadvantages_text = disadvantages_text[:950] + "...\n\nMais texto do que é permitido enviar..."
    
    character_embed.add_field(
        name="Desvantagens",
        value= f">>> {disadvantages_text}",
        inline=False
    )

    # Skills
    if len(skills_text) > 1000:
        skills_text = skills_text[:950] + "...\n\nMais texto do que é permitido enviar..."

    character_embed.add_field(
        name="Perícias",
        value= f">>> {skills_text}",
        inline=False
    )

    # Magias
    if len(magias_text) > 1000:
        magias_text = magias_text[:950] + "...\n\nMais texto do que é permitido enviar..."

    character_embed.add_field(
        name="Magias",
        value=f">>> {magias_text}",
        inline=False
    )

    return character_embed

@bot.tree.command(description="Envia a sua ficha de personagem no chat")
@app_commands.describe()
async def sheet(interact: discord.Interaction):
    user_id = str(interact.user.id)
    fichas_dir = "data/characters"
    
    if not os.path.exists(fichas_dir):
        await interact.response.send_message("Diretório de fichas não encontrado. Contate o Mestre", ephemeral=True)
        return

    # Collects all files belonging to this user
    user_files = [
        f for f in os.listdir(fichas_dir) 
        if f.startswith(f"{user_id}_") and f.endswith(".json")
    ]

    # Check the number of sheets found
    if len(user_files) == 0:
        await interact.response.send_message("Nenhuma ficha encontrada para o seu usuário.", ephemeral=True)
        return
        
    elif len(user_files) > 1:
        # Extracts the character names to display in the error message.
        char_names = [f[len(user_id) + 1 : -5] for f in user_files]
        names_text = ", ".join(char_names)
        
        await interact.response.send_message(
            f"⚠️ **Atenção:** Foram encontradas múltiplas fichas para o seu usuário. "
            f"Personagens: **{names_text}**. Mantenha apenas uma ficha na pasta.", 
            ephemeral=True
        )
        return

    # If it passed the checks, there is exactly 1 sheet
    file_name = user_files[0]
    file_path = os.path.join(fichas_dir, file_name)

    # Loads the sheet into memory
    with open(file_path, "r", encoding="utf-8") as f:
        player_sheet = json.load(f)

        player_embed = build_character_embed(sheet=player_sheet)

    await interact.response.send_message(embed=player_embed, ephemeral=True)

# NPC Sheet -------------------------------------------------------
# --Autocomplete
async def npc_autocomplete(interact: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    # Reads the folder instantly with every keystroke
    npc_files = glob.glob("data/npcs/*.json")
    
    choices = []
    for f in npc_files:
        file_name = os.path.basename(f).replace('.json', '') # Returns only the file name without the path and extension.
        display_name = file_name.replace('_', ' ').title()
        
        # Only adds to the list if the user's input matches the NPC's name
        if current.lower() in display_name.lower():
            choices.append(app_commands.Choice(name=display_name, value=file_name))
            
    # Discord requires returning a maximum of 25 filtered options
    return choices[:25]

@bot.tree.command(description="Envia a ficha de algum NPC no chat")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    npc="O NPC que você quer ver a ficha", 
    ephemeral="Se a mensagem pode ser lida por outros jogadores ou só pelo mestre"
    )
@app_commands.autocomplete(npc=npc_autocomplete)
@app_commands.choices(
    # This choice defines whether the message (character sheet) will 
    # be visible to the players (F) or visible only to the GM (T).
    ephemeral = [
        app_commands.Choice(name="Verdadeiro", value="V"),
        app_commands.Choice(name="Falso", value="F")
    ]
)
async def npc_sheet(interact: discord.Interaction, npc:str, ephemeral:str):
    
    is_ephemeral = True if ephemeral == "V" else False

    file_path = f"data/npcs/{npc}.json"

    # Prevention in case the GM tries to force a name that isn't on the list
    if not os.path.exists(file_path):
        await interact.response.send_message(" Arquivo do NPC não encontrado.", ephemeral=True)
        return

    # Load the JSON file into memory
    with open(file_path, "r", encoding="utf-8") as f:
        npc_sheet_data = json.load(f)
        # Embed 
        npc_embed = build_character_embed(sheet=npc_sheet_data)
    
    await interact.response.send_message(embed=npc_embed,ephemeral=is_ephemeral)

# Player Sheet ------------------------------------------------------
# --Autocomplete
async def player_autocomplete(interact: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    # Reads the folder instantly with every keystroke
    player_files = glob.glob("data/characters/*.json")
    
    choices = []
    for f in player_files:
        file_name = os.path.basename(f).replace('.json', '') # Returns only the file name without the path and extension.
        parts = file_name.split('_', 1) # Splits the string at the first underscore.
        display_name = parts[1] if len(parts) > 1 else file_name # Gets only the second part (the name). If there is no underscore, uses the full filename.

        
        # Only adds to the list if the user's input matches the Player's name
        if current.lower() in display_name.lower():
            choices.append(app_commands.Choice(name=display_name, value=file_name))
            
    # Discord requires returning a maximum of 25 filtered options
    return choices[:25]

@bot.tree.command(description="Envia a ficha de algum Player no chat")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    player="O nome do personagem",
    ephemeral="Se outros jogadores podem ver a ficha"
)
@app_commands.autocomplete(player=player_autocomplete)
@app_commands.choices(
    # This choice defines whether the message (character sheet) will 
    # be visible to the players (F) or visible only to the GM (T).
    ephemeral = [
        app_commands.Choice(name="Verdadeiro", value="V"),
        app_commands.Choice(name="Falso", value="F")
    ]
)
async def player_sheet(interact: discord.Interaction, player:str, ephemeral:str):
    
    is_ephemeral = True if ephemeral == "V" else False

    file_path = f"data/characters/{player}.json"

    # Prevention in case the GM tries to force a name that isn't on the list
    if not os.path.exists(file_path):
        await interact.response.send_message(" Arquivo do Personagem não encontrado.", ephemeral=True)
        return   

    # Load the JSON file into memory
    with open(file_path, "r", encoding="utf-8") as f:
        player_sheet_data = json.load(f)
        # Embed 
        player_embed = build_character_embed(sheet=player_sheet_data)
    
    await interact.response.send_message(embed=player_embed,ephemeral=is_ephemeral)

# Run the Bot
initialize_system_database()
bot.run(config["BOT"]["Token"])
