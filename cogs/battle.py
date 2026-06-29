import discord
from discord import app_commands
from discord.ext import commands

from random import randint

class Battle(commands.Cog):
    """
    
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Dependency injection extraction should occur strictly here.
        # Example: self.config = self.bot.config

    # Damage Command ------------------------------------------------
    @app_commands.command(description="Calcula dano de um ataque")
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
        self,
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

async def setup(bot: commands.Bot):
    """
    Mandatory asynchronous entry point to load the extension.
    """
    await bot.add_cog(Battle(bot))