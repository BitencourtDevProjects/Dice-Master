# LIBRARIES =====================================================
# Discord Libraries
import discord
from discord.ext import commands
from discord import app_commands

# Other Libraries
import configparser
from random import randint
import os
import glob
import json

# ===============================================================

# CONFIGURATIONS ===============================================================================================================
# Configparser --------------------------------------------------
config = configparser.ConfigParser()  # init
config.read("config.ini")  # Definition of the configuration file

# Definition of permissions -------------------------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(
    config["BOT"]["Prefix"], intents=intents
)  # The config['BOT']['Prefix'] defines the bot command prefix

# USEFUL FUNCTIONS =============================================================================================================
def sheet_data_extractor(dados: dict, path: list): 
    """Safely extracts values from character and NPC sheets stored in JSON format,
    guaranteeing that no errors are raised if the requested path or value 
    does not exist in the sheet.

    Args:
        dados (dict): The dictionary containing the character or NPC sheet data.
        path (list): A list of sequential keys leading to the desired attribute.

    Returns:
        any: The value found at the end of the path, or None if the path is missing.

    ---

    Extrai com segurança valores das fichas de personagens e NPCs armazenadas 
    em formato JSON, garantindo que nenhum erro seja disparado caso o caminho 
    ou valor solicitado não exista na ficha.

    Args:
        dados (dict): O dicionário contendo os dados da ficha do personagem ou NPC.
        path (list): Uma lista de chaves que representa o caminho sequencial até o atributo.

    Returns:
        any: O valor encontrado no final do caminho, ou None se o caminho não existir.
    """
    item = dados
    for chave in path:
        if isinstance(item, dict):
            item = item.get(chave)
        else:
            return None
            
    return item


# NORMAL COMMANDS ==============================================================================================================
# Sync command --------------------------------------------------
@bot.command(name="sync")
@commands.is_owner()  # Ensures that only the bot owner can run this command
async def sync(ctx):
    try:
        syncs = await bot.tree.sync()
        await ctx.reply(f"{len(syncs)} Commands successfully synchronized")

    except Exception as e:
        await ctx.reply(f"Commands not synchronized {e}")


# SLASH COMMANDS ===============================================================================================================
# Skill Command -------------------------------------------------
@bot.tree.command(description="Realiza os testes de Habilidade")
@app_commands.describe(
    nh="Seu Nível de Habilidade na perícia",
    modificador="Modificador de Dificuldade",
)
async def skill(interact: discord.Interaction, nh: int, modificador: int):

    player_id = interact.user.id

    # Dice Roll
    if player_id in pending_controls:
        fate = pending_controls.pop(player_id)
        dices = hdm_dices(nh=nh, fate=fate)

    else:
        dices = [randint(1, 6) for _ in range(3)]

    dice_pool = sum(dices)
    effective_nh = nh + modificador

    if effective_nh < 0:  # Ensures effective NH is never less than 0
        effective_nh = 0

    # Embeds
    skill_embed = discord.Embed()

    # Validation of success
    if dice_pool == 18:  # Verification of critical failures
        skill_embed.title = "FALHA CRÍTICA!"
        skill_embed.color = discord.Color.brand_red()

    elif dice_pool == 17:  # Verification of critical failures
        if effective_nh <= 15:
            skill_embed.title = "FALHA CRÍTICA!"
            skill_embed.color = discord.Color.brand_red()
        else:
            skill_embed.title = "FALHA"
            skill_embed.color = discord.Color.red()

    elif dice_pool <= effective_nh:  # If the roll was a success
        if dice_pool <= 4:
            skill_embed.title = "SUCESSO DECISIVO!"
            skill_embed.color = discord.Color.gold()

        else:
            if (
                effective_nh - dice_pool >= 10
            ):  # Checks if the margin of success is 10 or greater
                skill_embed.title = "SUCESSO DECISIVO!"
                skill_embed.color = discord.Color.gold()

            else:
                skill_embed.title = "SUCESSO!"
                skill_embed.color = discord.Color.green()

    else:  # If the roll was not a success
        if (
            dice_pool - effective_nh >= 10
        ):  # Checks if the margin of failure is 10 or greater
            skill_embed.title = "FALHA CRÍTICA!"
            skill_embed.color = discord.Color.brand_red()
        else:
            skill_embed.title = "FALHA"
            skill_embed.color = discord.Color.red()

    # construction of the emdice_countbed
    skill_embed.add_field(
        name="Parada de Dados", value=f"`{dices} = {dice_pool}`", inline=False
    )
    skill_embed.add_field(
        name="Nível de Habilidade",
        value=f"NH Basico: {nh}\nModificador: {modificador}\n`NH Efetivo: {effective_nh}`",
        inline=False,
    )

    if skill_embed.title == "SUCESSO DECISIVO!" or skill_embed.title == "SUCESSO!":
        skill_embed.add_field(
            name="Margem de Vitória",
            value=f"{effective_nh} - {dice_pool} = {effective_nh - dice_pool}",
            inline=False,
        )
    else:
        skill_embed.add_field(
            name="Margem de Derrota",
            value=f"{dice_pool} - {effective_nh} = {dice_pool - effective_nh}",
            inline=False,
        )

    await interact.response.send_message(embed=skill_embed)


# Damage Command ------------------------------------------------
@bot.tree.command(description="Calcula dano de um ataque")
@app_commands.describe(
    st="Força do seu personagem",
    modificador="Modificador de dano dado pela arma",
    atk_type="Escoha se é um golpe de ponta ou um golpe em Balanço",
)
@app_commands.choices(
    atk_type=[
        app_commands.Choice(name="Golpe de Ponta", value=0),
        app_commands.Choice(name="Golpe em Balanço", value=1),
    ]
)
async def dmg(
    interact: discord.Interaction,
    st: int,
    modificador: int,
    atk_type: app_commands.Choice[int]
):

    # The damage table maps the damage caused by different ST levels. Information retrieved from the GURPS Basic Set book.
    damage_table = {
        1: ([1, -6], [1, -5]),
        2: ([1, -6], [1, -5]),
        3: ([1, -5], [1, -4]),
        4: ([1, -5], [1, -4]),
        5: ([1, -4], [1, -3]),
        6: ([1, -4], [1, -3]),
        7: ([1, -3], [1, -2]),
        8: ([1, -3], [1, -2]),
        9: ([1, -2], [1, -1]),
        10: ([1, -2], [1, 0]),
        11: ([1, -1], [1, 1]),
        12: ([1, -1], [1, 2]),
        13: ([1, 0], [2, -1]),
        14: ([1, 0], [2, 0]),
        15: ([1, 1], [2, 1]),
        16: ([1, 1], [2, 2]),
        17: ([1, 2], [3, -1]),
        18: ([1, 2], [3, 0]),
        19: ([2, -1], [3, 1]),
        20: ([2, -1], [3, 2]),
        21: ([2, 0], [4, -1]),
        22: ([2, 0], [4, 0]),
        23: ([2, 1], [4, 1]),
        24: ([2, 1], [4, 2]),
        25: ([2, 2], [5, -1]),
        26: ([2, 2], [5, 0]),
        27: ([3, -1], [5, 1]),
        28: ([3, -1], [5, 1]),
        29: ([3, 0], [5, 2]),
        30: ([3, 0], [5, 2]),
        31: ([3, 1], [6, -1]),
        32: ([3, 1], [6, -1]),
        33: ([3, 2], [6, 0]),
        34: ([3, 2], [6, 0]),
        35: ([4, -1], [6, 1]),
        36: ([4, -1], [6, 1]),
        37: ([4, 0], [6, 2]),
        38: ([4, 0], [6, 2]),
        39: ([4, 1], [7, -1]),
        40: ([4, 1], [7, -1]),
        45: ([5, 0], [7, 1]),
        50: ([5, 2], [8, -1]),
        55: ([6, 0], [8, 1]),
        60: ([7, -1], [9, 0]),
        65: ([7, 1], [9, 2]),
        70: ([8, 0], [10, 0]),
        75: ([8, 2], [10, 2]),
        80: ([9, 0], [11, 0]),
        85: ([9, 2], [11, 2]),
        90: ([10, 0], [12, 0]),
        95: ([10, 2], [12, 2]),
        100: ([11, 0], [13, 0]),
    }

    if st <= 0:
        basic_damage = ([0, 0], [0, 0])
    # Rule for ST above 100: adds 1d to GdP and GeB for every 10 whole points
    elif st > 100:
        extra_dice = (st - 100) // 10
        gdp_dice = 11 + extra_dice
        geb_dice = 13 + extra_dice
        basic_damage = ([gdp_dice, 0], [geb_dice, 0])
    # If the ST is exactly in the table, returns it directly
    elif st in damage_table:
        basic_damage = damage_table[st]
    # If it is between 40 and 100 and not in the table, rounds down to the nearest multiple of 5
    else:
        rounded_st = (st // 5) * 5
        basic_damage = damage_table[rounded_st]

    # Here it takes the value (0 or 1) stored in the atk_type choice and uses it to look up the correct value in the dictionary
    dice_count, st_mod = basic_damage[atk_type.value] 

    # Damage calculation
    dices = [randint(1, 6) for _ in range(dice_count)]
    dice_sum = sum(dices)
    damage = dice_sum + st_mod + modificador

    # penetrating Damage


    # Embed
    dmg_embed = discord.Embed()
    signal = "+" if st_mod >= 0 else "-"

    dmg_embed.title = "DANO"
    dmg_embed.color = discord.Color.brand_red()
    dmg_embed.add_field(name="Força", value=st, inline=False)
    dmg_embed.add_field(
        name="Tipo de Ataque",
        value=f"{atk_type.name}\n{dice_count}d {signal} {abs(st_mod)}",
        inline=False,
    )
    dmg_embed.add_field(
        name="Resultado da Rolagem",
        value=f"\n`Dados: {dices} = {dice_sum}`\nModificador de Força: {st_mod}\nModificador de Arma: {modificador}\n\n**Total:** {damage}",
        inline=False,
    )

    await interact.response.send_message(embed=dmg_embed)


# Roll Command ---------------------------------------------------
@bot.tree.command(
    description="Rola Genericamente um número de dados com algum modiificador"
)
@app_commands.describe(
    num_dados="Número de dados que serão rolados",
    modificador="Qualquer modificador que precise ser aplicado",
)
async def roll(interact: discord.Interaction, num_dados: int, modificador: int):
    dices = [randint(1, 6) for _ in range(num_dados)]
    dice_pool = sum(dices)

    # Embed
    roll_embed = discord.Embed()

    roll_embed.title = "ROLAGEM"
    roll_embed.color = discord.Color.green()
    roll_embed.add_field(
        name="Rolagem",
        value=f"`Dados: {dices} = {dice_pool}`\nModificador: {modificador}\n\n**Total:** {dice_pool + modificador}",
    )

    await interact.response.send_message(embed=roll_embed)


# Quick Dispute Command -------------------------------------------
@bot.tree.command(description="Realiza uma disputá Rápida de habilidades")
@app_commands.describe(
    nh1="Seu NH",
    modificador1="Seus modificadores de dificuldade",
    nh2="Nh do seu adversário",
    modificador2="Modificadores de dificuldade do seu adversário",
)
async def qkd(
    interact: discord.Interaction,
    nh1: int,
    modificador1: int,
    nh2: int,
    modificador2: int,
):

    player_id = interact.user.id

    effective_nh1 = nh1 + modificador1
    effective_nh2 = nh2 + modificador2

    # Plot Device Block
    if player_id in pending_controls:
        fate = pending_controls.pop(player_id)

        if fate == 0:  # Both pass, you win by the margin of success
            loop_count = 0
            while True:
                dices1 = hdm_dices(effective_nh1, 0)
                dices2 = hdm_dices(effective_nh2, 0)
                if (effective_nh1 - sum(dices1)) > (effective_nh2 - sum(dices2)):
                    break
                loop_count += 1

                if loop_count > 100:
                    dices2 = hdm_dices(effective_nh2, 1)
                    break

        elif fate == 1:  # Both pass, you lose by the margin of success
            loop_count = 0
            while True:
                dices1 = hdm_dices(effective_nh1, 0)
                dices2 = hdm_dices(effective_nh2, 0)
                if (effective_nh1 - sum(dices1)) < (effective_nh2 - sum(dices2)):
                    break
                loop_count += 1

                if loop_count > 100:
                    dices1 = hdm_dices(effective_nh1, 1)
                    break

        elif fate == 2:  # You pass, the enemy fails.
            dices1 = hdm_dices(effective_nh1, 0)
            dices2 = hdm_dices(effective_nh2, 1)

        elif fate == 3:  # You fail, the enemy passes.
            dices1 = hdm_dices(effective_nh1, 1)
            dices2 = hdm_dices(effective_nh2, 0)

    else:
        dices1 = [randint(1, 6) for _ in range(3)]
        dices2 = [randint(1, 6) for _ in range(3)]

    dice_pool1 = sum(dices1)
    effective_nh1 = nh1 + modificador1
    success_roll1 = False if dice_pool1 > effective_nh1 else True
    margin1 = effective_nh1 - dice_pool1

    dice_pool2 = sum(dices2)
    effective_nh2 = nh2 + modificador2
    success_roll2 = False if dice_pool2 > effective_nh2 else True
    margin2 = effective_nh2 - dice_pool2

    # Embed
    qkd_embed = discord.Embed()

    if success_roll1 is True and success_roll2 is False:
        qkd_embed.title = "SUCESSO POR ROLAGEM!"
        qkd_embed.description = (
            "Você obteve um sucesso no teste e seu oponente um fracasso"
        )
        qkd_embed.color = discord.Color.green()

    elif success_roll1 is False and success_roll2 is True:
        qkd_embed.title = "FRACASSO POR ROLAGEM!"
        qkd_embed.description = (
            "Você obteve um fracasso no teste e seu oponente um sucesso"
        )
        qkd_embed.color = discord.Color.red()

    elif margin1 > margin2:
        qkd_embed.title = "SUCESSO POR MARGEM DE TESTE!"
        qkd_embed.color = discord.Color.green()
        qkd_embed.description = "Resultado decidido pela margem do teste."

    elif margin1 == margin2:
        qkd_embed.title = "EMPATE!"
        qkd_embed.color = discord.Color.greyple()
        qkd_embed.description = "Empate"

    else:
        qkd_embed.title = "FRACASSO POR MARGEM DE TESTE!"
        qkd_embed.color = discord.Color.red()
        qkd_embed.description = "Resultado decidido pela margem do teste."

    qkd_embed.add_field(
        name="Você",
        value=f"`Dados: {dices1} = {dice_pool1}`\nNH Base: {nh1}\nModificador: {modificador1}\n`NH Efetivo: {effective_nh1}`\nSucesso: {"Sim" if success_roll1 is True else "Não"}\n`Margem: {margin1}`",
        inline=False,
    )
    qkd_embed.add_field(
        name="Oponente",
        value=f"`Dados: {dices2} = {dice_pool2}`\nNH Base: {nh2}\nModificador: {modificador2}\n`NH Efetivo: {effective_nh2}`\nSucesso: {"Sim" if success_roll2 is True else "Não"}\n`Margem: {margin2}`",
        inline=False,
    )
    qkd_embed.add_field(
        name="Diferença das Margens de Sucesso",
        value=f"`{margin1} - ({margin2}) = {margin1 - margin2}`",
        inline=False
    )

    await interact.response.send_message(embed=qkd_embed)


# Debug -----------------------------------------------------------
pending_controls = {}


def hdm_dices(nh: int, fate: int):
    # --- SAFETY CHECKS (Prevents infinite loops) ---

    # If NH is 4 or less, any success will roll a 3 or 4 (Critical Success)
    if fate == 0 and nh <= 4:
        fate = 2

    # If NH is 26 or more, the worst possible success (16) will still have a margin >= 10 (Critical Success)
    if fate == 0 and nh >= 26:
        fate = 2

    if fate == 0:  # Normal Success
        while True:
            dices = [randint(1, 6) for _ in range(3)]
            dice_pool = sum(dices)
            if nh >= 15:
                if dice_pool <= nh and nh - dice_pool < 10:
                    return dices
            elif dice_pool <= nh and dice_pool > 4:
                return dices
    elif fate == 1:  # Normal Failure
        while True:
            dices = [randint(1, 6) for _ in range(3)]
            dice_pool = sum(dices)
            if nh >= 16:
                if dice_pool == 17:
                    return dices
            else:
                if dice_pool > nh and dice_pool < 17:
                    return dices
    elif fate == 2:  # Critical Success
        while True:
            dices = [randint(1, 6) for _ in range(3)]
            dice_pool = sum(dices)
            if nh >= 15:
                if nh - dice_pool >= 10:
                    return dices
            elif dice_pool <= 4:
                return dices
    else:  # fate == 3 - Critical Failure
        # This block checks if the effective skill is 15 or less.
        # If so, a roll of 17 is a critical failure; otherwise, only 18 is a critical failure.
        while True:
            dices = [randint(1, 6) for _ in range(3)]
            dice_pool = sum(dices)
            if nh <= 7:
                if dice_pool - nh >= 10:
                    return dices
            if nh <= 15:
                if dice_pool >= 17:
                    return dices
            elif dice_pool == 18:
                return dices


@bot.tree.command(description="Um comando feito para testar o código e debug")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    jogador="O jogaoddr que terá o teste alterado",
    fate="Escolha de qual será o próximo resultado do usuário",
)
@app_commands.choices(
    fate=[
        app_commands.Choice(name="Sucesso", value=0),
        app_commands.Choice(name="Fracasso", value=1),
        app_commands.Choice(name="Sucesso Decisivo", value=2),
        app_commands.Choice(name="Falha Crítica", value=3),
    ]
)
async def hdm(
    interact: discord.Interaction,
    jogador: discord.Member,
    fate: app_commands.Choice[int],
):
    if interact.user.id != int(config["BOT"]["DM_ID"]):
        await interact.response.send_message(
            "Erro. Você não tem permissão para usar os comandos de Debug"
        )
        return

    pending_controls[jogador.id] = (
        fate.value
    )  # inserting the user ID and their fate into the pending_controls dictionary.

    await interact.response.send_message(
        content=f"A próxima rolagem de {jogador.mention} será {fate.name}",
        ephemeral=True,
    )


# Reaction Test ---------------------------------------------------
@bot.tree.command(description="Realiza a rolagem de um teste de reação")
@app_commands.describe(modificador="Soma dos modificadores de reação que você tem")
async def react(interact: discord.Interaction, modificador: int):
    player_id = interact.user.id

    # The first part of the if-block validates whether the user is included in the
    # `pending_controls` dictionary. If so, it initiates the validation of which "fate"
    # was chosen by the DM and returns a matching result. The second part runs the dice
    # selection normally.
    if player_id in pending_controls:
        fate = pending_controls.pop(player_id)

        # Safeguards: The minimum and maximum that 3d6 can roll with the current modifier
        min_possible = 3 + modificador
        max_possible = 18 + modificador

        if fate == 0:  # Sucesso (Total between 10 and 15)
            if max_possible < 10:
                dices = [6, 6, 6]
            elif min_possible > 15:
                dices = [1, 1, 1]
            else:
                while True:
                    dices = [randint(1, 6) for _ in range(3)]
                    if 10 <= sum(dices) + modificador <= 15:
                        break

        elif fate == 1:  # Fracasso (Total between 4 and 9)
            if max_possible < 4:
                dices = [6, 6, 6]
            elif min_possible > 9:
                dices = [1, 1, 1]
            else:
                while True:
                    dices = [randint(1, 6) for _ in range(3)]
                    if 4 <= sum(dices) + modificador <= 9:
                        break

        elif fate == 2:  # Sucesso Decisivo (Total 16 or more)
            if max_possible < 16:
                dices = [6, 6, 6]
            else:
                while True:
                    dices = [randint(1, 6) for _ in range(3)]
                    if sum(dices) + modificador >= 16:
                        break

        else:  # Fracasso Decisivo (Total 3 or less)
            if min_possible > 3:
                dices = [1, 1, 1]
            else:
                while True:
                    dices = [randint(1, 6) for _ in range(3)]
                    if sum(dices) + modificador <= 3:
                        break

    else:
        dices = [randint(1, 6) for _ in range(3)]

    dice_pool = sum(dices)
    total = dice_pool + modificador

    # Embeds
    react_embed = discord.Embed()

    if total <= 0:
        react_embed.title = "REAÇÃO DESASTROSA"
        react_embed.color = discord.Color.red()
    elif total <= 3:
        react_embed.title = "REAÇÃO MUITO RUIM"
        react_embed.color = discord.Color.red()
    elif total <= 6:
        react_embed.title = "REAÇÃO RUIM"
        react_embed.color = discord.Color.orange()
    elif total <= 9:
        react_embed.title = "REAÇÃO FRACA"
        react_embed.color = discord.Color.yellow()
    elif total <= 12:
        react_embed.title = "REAÇÃO NEUTRA"
        react_embed.color = discord.Color.greyple()
    elif total <= 15:
        react_embed.title = "REAÇÃO BOA"
        react_embed.color = discord.Color.green()
    elif total <= 18:
        react_embed.title = "REAÇÃO MUITO BOA"
        react_embed.color = discord.Color.green()
    else:
        react_embed.title = "REAÇÃO EXCELENTE"
        react_embed.color = discord.Color.blue()

    react_embed.add_field(
        name="Dados",
        value=f"`Dados: {dices} = {dice_pool}`\nModificador: {modificador}\n\n**Total: {total}**",
        inline= False
    )

    await interact.response.send_message(embed=react_embed)

# Panic -----------------------------------------------------------
@bot.tree.command(description="Realiza uma verificação de Pânico")
@app_commands.describe(vontade="Seu Valor de Vontade", modificador="Soma dos modificadores de dificuldade")
async def panic(interact: discord.Interaction, vontade:int, modificador:int):
    player_id = interact.user.id

    # Dice Roll
    if player_id in pending_controls:
        fate = pending_controls.pop(player_id)
        dices = hdm_dices(nh=vontade, fate=fate)

    else:
        dices = [randint(1, 6) for _ in range(3)]

    dice_pool = sum(dices)
    effective_nh = vontade + modificador
    
    if effective_nh < 0:  # Ensures effective NH is never less than 0
        effective_nh = 0

    # Embeds
    panic_embed = discord.Embed()

    # Validation of success
    if dice_pool == 18:  # Verification of critical failures
        panic_embed.title = "FALHA CRÍTICA!"
        panic_embed.color = discord.Color.brand_red()

    elif dice_pool == 17:  # Verification of critical failures
        if effective_nh <= 15:
            panic_embed.title = "FALHA CRÍTICA!"
            panic_embed.color = discord.Color.brand_red()
        else:
            panic_embed.title = "FALHA"
            panic_embed.color = discord.Color.red()

    elif dice_pool <= effective_nh:  # If the roll was a success
        if dice_pool <= 4:
            panic_embed.title = "SUCESSO DECISIVO!"
            panic_embed.color = discord.Color.gold()

        else:
            if (
                effective_nh - dice_pool >= 10
            ):  # Checks if the margin of success is 10 or greater
                panic_embed.title = "SUCESSO DECISIVO!"
                panic_embed.color = discord.Color.gold()

            else:
                panic_embed.title = "SUCESSO!"
                panic_embed.color = discord.Color.green()

    else:  # If the roll was not a success
        if (
            dice_pool - effective_nh >= 10
        ):  # Checks if the margin of failure is 10 or greater
            panic_embed.title = "FALHA CRÍTICA!"
            panic_embed.color = discord.Color.brand_red()
        else:
            panic_embed.title = "FALHA"
            panic_embed.color = discord.Color.red()

    if panic_embed.title == "SUCESSO DECISIVO!" or panic_embed.title == "SUCESSO!":
        # construction of the emdice_countbed
        panic_embed.title = "RESISTIU AO PÂNICO"
        panic_embed.add_field(
            name="Parada de Dados", value=f"`{dices} = {dice_pool}`", inline=False
        )
        panic_embed.add_field(
            name="Nível de Vontade",
            value=f"NH Basico: {vontade}\nModificador: {modificador}\n`NH Efetivo: {effective_nh}`",
            inline=False,
        )
        panic_embed.add_field(
            name="Margem de Vitória",
            value=f"{effective_nh} - {dice_pool} = {effective_nh - dice_pool}",
            inline=False,
        )
    else:
        panic_embed.title = "SUCUMBIU AO PÂNICO"
        dices_panic = [randint(1, 6) for _ in range(3)]
        dice_pool_panic = sum(dices_panic)

        panic_value = dice_pool_panic + (dice_pool - effective_nh)

        panic_embed.description = "Tabela de pânico pode ser encontrada em GURPS Módulo Básico Pág: 361"
        panic_embed.add_field(
            name="Valor do teste de Pânico",
            value=panic_value,
            inline=False,
        )







    await interact.response.send_message(embed=panic_embed)

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
bot.run(config["BOT"]["Token"])
