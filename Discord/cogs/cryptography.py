
from discord.ext import commands

import hashlib
import sys
from typing import Optional
import zlib

from cryptography.hazmat.backends.openssl import backend as openssl_backend
from cryptography.hazmat.primitives import hashes as crypto_hashes
import pygost.gost28147
import pygost.gost28147_mac
import pygost.gost34112012
import pygost.gost341194
import pygost.gost3412

from utilities import checks

sys.path.insert(0, "..")
from units.cryptography import (decode_caesar_cipher, encode_caesar_cipher, 
								decode_morse_code, encode_morse_code, 
								UnitOutputError)
sys.path.pop(0)

def setup(bot):
	bot.add_cog(Cryptography(bot))

class Cryptography(commands.Cog):
	
	def __init__(self, bot):
		self.bot = bot
	
	async def cog_check(self, ctx):
		return await checks.not_forbidden().predicate(ctx)
	
	# TODO: not forbidden global check?
	
	@commands.group(aliases = ["decrpyt"], invoke_without_command = True, case_insensitive = True)
	async def decode(self, ctx):
		'''Decode coded messages'''
		await ctx.send_help(ctx.command)
	
	@decode.group(name = "caesar", aliases = ["rot"], 
					invoke_without_command = True, case_insensitive = True)
	async def decode_caesar(self, ctx, key: int, *, message: str):
		'''Decode caesar cipher'''
		await ctx.embed_reply(decode_caesar_cipher(message, key))
	
	@decode_caesar.command(name = "brute")
	async def decode_caesar_brute(self, ctx, message : str):
		'''Brute force decode caesar cipher'''
		# TODO: Paginate if too long
		await ctx.embed_reply('\n'.join(f"{key}: {decode_caesar_cipher(message, key)}" for key in range(26)))
	
	@decode.group(name = "gost", aliases = ["гост"], 
					invoke_without_command = True, case_insensitive = True)
	async def decode_gost(self, ctx):
		'''
		Russian Federation/Soviet Union GOST
		Межгосударственный стандарт
		From GOsudarstvennyy STandart
		(ГОсударственный СТандарт)
		'''
		await ctx.send_help(ctx.command)
	
	@decode_gost.group(name = "28147-89", aliases = ["магма", "magma"], 
						invoke_without_command = True, case_insensitive = True)
	async def decode_gost_28147_89(self, ctx):
		'''
		GOST 28147-89 block cipher
		Also known as Магма or Magma
		key length must be 32 (256-bit)
		'''
		# TODO: Add decode magma alias
		await ctx.send_help(ctx.command)
	
	@decode_gost_28147_89.command(name = "cbc")
	async def decode_gost_28147_89_cbc(self, ctx, key : str, *, data : str):
		'''Magma with CBC mode of operation'''
		try:
			await ctx.embed_reply(pygost.gost28147.cbc_decrypt(key.encode("UTF-8"), bytearray.fromhex(data)).decode("UTF-8"))
		except ValueError as e:
			await ctx.embed_reply(f":no_entry: Error: {e}")
	
	@decode_gost_28147_89.command(name = "cfb")
	async def decode_gost_28147_89_cfb(self, ctx, key : str, *, data : str):
		'''Magma with CFB mode of operation'''
		try:
			await ctx.embed_reply(pygost.gost28147.cfb_decrypt(key.encode("UTF-8"), bytearray.fromhex(data)).decode("UTF-8"))
		except ValueError as e:
			await ctx.embed_reply(f":no_entry: Error: {e}")
	
	@decode_gost_28147_89.command(name = "cnt")
	async def decode_gost_28147_89_cnt(self, ctx, key : str, *, data : str):
		'''Magma with CNT mode of operation'''
		try:
			await ctx.embed_reply(pygost.gost28147.cnt(key.encode("UTF-8"), bytearray.fromhex(data)).decode("UTF-8"))
		except ValueError as e:
			await ctx.embed_reply(f":no_entry: Error: {e}")
	
	@decode_gost_28147_89.command(name = "ecb")
	async def decode_gost_28147_89_ecb(self, ctx, key : str, *, data : str):
		'''
		Magma with ECB mode of operation
		data block size must be 8 (64-bit)
		This means the data length must be a multiple of 8
		'''
		try:
			await ctx.embed_reply(pygost.gost28147.ecb_decrypt(key.encode("UTF-8"), bytearray.fromhex(data)).decode("UTF-8"))
		except ValueError as e:
			await ctx.embed_reply(f":no_entry: Error: {e}")
	
	@decode_gost.command(name = "34.12-2015", aliases = ["кузнечик", "kuznyechik"])
	async def decode_gost_34_12_2015(self, ctx, key : str, *, data : str):
		'''
		GOST 34.12-2015 128-bit block cipher
		Also known as Кузнечик or Kuznyechik
		key length >= 32, data length >= 16
		'''
		# TODO: Add decode kuznyechik alias
		if len(key) < 32:
			return await ctx.embed_reply(":no_entry: Error: key length must be at least 32")
		if len(data) < 16:
			return await ctx.embed_reply(":no_entry: Error: data length must be at least 16")
		await ctx.embed_reply(pygost.gost3412.GOST3412Kuznechik(key.encode("UTF-8")).decrypt(bytearray.fromhex(data)).decode("UTF-8"))
	
	@decode.command(name = "morse")
	async def decode_morse(self, ctx, *, message : str):
		'''Decodes morse code'''
		try:
			await ctx.embed_reply(decode_morse_code(message))
		except UnitOutputError as e:
			await ctx.embed_reply(f":no_entry: Error: {e}")
	
	@decode.command(name = "qr")
	async def decode_qr(self, ctx, file_url: Optional[str]):
		'''
		Decodes QR codes
		Input a file url or attach an image
		'''
		if not file_url:
			if ctx.message.attachments:
				file_url = ctx.message.attachments[0].url
			else:
				return await ctx.embed_reply(":no_entry: Please input a file url or attach an image")
		# TODO: use textwrap
		url = f"https://api.qrserver.com/v1/read-qr-code/"
		params = {"fileurl": file_url}
		async with ctx.bot.aiohttp_session.get(url, params = params) as resp:
			if resp.status == 400:
				return await ctx.embed_reply(":no_entry: Error")
			data = await resp.json()
		if data[0]["symbol"][0]["error"]:
			return await ctx.embed_reply(f":no_entry: Error: {data[0]['symbol'][0]['error']}")
		decoded = data[0]["symbol"][0]["data"].replace("QR-Code:", "")
		if len(decoded) > ctx.bot.EMBED_DESCRIPTION_CHARACTER_LIMIT:
			return await ctx.embed_reply(decoded[:ctx.bot.EDCL - 3] + "...", 
											footer_text = "Decoded message exceeded character limit")
			# EDCL: Embed Description Character Limit
		await ctx.embed_reply(decoded)
	
	@decode.command(name = "reverse")
	async def decode_reverse(self, ctx, *, message : str):
		'''Reverses text'''
		await ctx.embed_reply(message[::-1])
	
	@commands.group(aliases = ["encrypt"], invoke_without_command = True, case_insensitive = True)
	async def encode(self, ctx):
		'''Encode messages'''
		await ctx.send_help(ctx.command)
	
	@encode.command(name = "adler32", aliases = ["adler-32"])
	async def encode_adler32(self, ctx, *, message : str):
		'''Compute Adler-32 checksum'''
		await ctx.embed_reply(zlib.adler32(message.encode("UTF-8")))
	
	@encode.command(name = "blake2b")
	async def encode_blake2b(self, ctx, *, message : str):
		'''64-byte digest BLAKE2b'''
		digest = crypto_hashes.Hash(crypto_hashes.BLAKE2b(64), backend = openssl_backend)
		digest.update(message.encode("UTF-8"))
		await ctx.embed_reply(digest.finalize())
	
	@encode.command(name = "blake2s")
	async def encode_blake2s(self, ctx, *, message : str):
		'''32-byte digest BLAKE2s'''
		digest = crypto_hashes.Hash(crypto_hashes.BLAKE2s(32), backend = openssl_backend)
		digest.update(message.encode("UTF-8"))
		await ctx.embed_reply(digest.finalize())
	
	@encode.command(name = "caesar", aliases = ["rot"])
	async def encode_caesar(self, ctx, key : int, *, message : str):
		'''Encode a message using a caesar cipher'''
		await ctx.embed_reply(encode_caesar_cipher(message, key))
	
	@encode.command(name = "crc32", aliases = ["crc-32"])
	async def encode_crc32(self, ctx, *, message : str):
		'''Compute CRC32 checksum'''
		await ctx.embed_reply(zlib.crc32(message.encode("UTF-8")))
	
	@encode.group(name = "gost", aliases = ["гост"], 
					invoke_without_command = True, case_insensitive = True)
	async def encode_gost(self, ctx):
		'''
		Russian Federation/Soviet Union GOST
		Межгосударственный стандарт
		From GOsudarstvennyy STandart
		(ГОсударственный СТандарт)
		'''
		await ctx.send_help(ctx.command)
	
	@encode_gost.group(name = "28147-89", aliases = ["магма", "magma"], 
						invoke_without_command = True, case_insensitive = True)
	async def encode_gost_28147_89(self, ctx):
		'''
		GOST 28147-89 block cipher
		Also known as Магма or Magma
		key length must be 32 (256-bit)
		'''
		# TODO: Add encode magma alias
		await ctx.send_help(ctx.command)
	
	@encode_gost_28147_89.command(name = "cbc")
	async def encode_gost_28147_89_cbc(self, ctx, key : str, *, data : str):
		'''Magma with CBC mode of operation'''
		try:
			await ctx.embed_reply(pygost.gost28147.cbc_encrypt(key.encode("UTF-8"), data.encode("UTF-8")).hex())
		except ValueError as e:
			await ctx.embed_reply(f":no_entry: Error: {e}")
	
	@encode_gost_28147_89.command(name = "cfb")
	async def encode_gost_28147_89_cfb(self, ctx, key : str, *, data : str):
		'''Magma with CFB mode of operation'''
		try:
			await ctx.embed_reply(pygost.gost28147.cfb_encrypt(key.encode("UTF-8"), data.encode("UTF-8")).hex())
		except ValueError as e:
			await ctx.embed_reply(f":no_entry: Error: {e}")
	
	@encode_gost_28147_89.command(name = "cnt")
	async def encode_gost_28147_89_cnt(self, ctx, key : str, *, data : str):
		'''Magma with CNT mode of operation'''
		try:
			await ctx.embed_reply(pygost.gost28147.cnt(key.encode("UTF-8"), data.encode("UTF-8")).hex())
		except ValueError as e:
			await ctx.embed_reply(f":no_entry: Error: {e}")
	
	@encode_gost_28147_89.command(name = "ecb")
	async def encode_gost_28147_89_ecb(self, ctx, key : str, *, data : str):
		'''
		Magma with ECB mode of operation
		data block size must be 8 (64-bit)
		This means the data length must be a multiple of 8
		'''
		try:
			await ctx.embed_reply(pygost.gost28147.ecb_encrypt(key.encode("UTF-8"), data.encode("UTF-8")).hex())
		except ValueError as e:
			await ctx.embed_reply(f":no_entry: Error: {e}")
	
	@encode_gost_28147_89.command(name = "mac")
	async def encode_gost_28147_89_mac(self, ctx, key : str, *, data : str):
		'''Magma with MAC mode of operation'''
		try:
			mac = pygost.gost28147_mac.MAC(key = key.encode("UTF-8"))
			mac.update(data.encode("UTF-8"))
			await ctx.embed_reply(mac.hexdigest())
		except ValueError as e:
			await ctx.embed_reply(f":no_entry: Error: {e}")
	
	@encode_gost.group(name = "34.11-2012", aliases = ["стрибог", "streebog"], 
						invoke_without_command = True, case_insensitive = True)
	async def encode_gost_34_11_2012(self, ctx):
		'''
		GOST 34.11-2012 hash function
		Also known as Стрибог or Streebog
		'''
		# TODO: Add encode streebog-256 and encode streebog-512 aliases
		await ctx.send_help(ctx.command)
	
	@encode_gost_34_11_2012.command(name = "256")
	async def encode_gost_34_11_2012_256(self, ctx, *, data : str):
		'''
		GOST 34.11-2012 256-bit hash function
		Also known as Streebog-256
		'''
		await ctx.embed_reply(pygost.gost34112012.GOST34112012(data.encode("UTF-8"), digest_size = 32).hexdigest())
	
	@encode_gost_34_11_2012.command(name = "512")
	async def encode_gost_34_11_2012_512(self, ctx, *, data : str):
		'''
		GOST 34.11-2012 512-bit hash function
		Also known as Streebog-512
		'''
		await ctx.embed_reply(pygost.gost34112012.GOST34112012(data.encode("UTF-8"), digest_size = 64).hexdigest())
	
	@encode_gost.command(name = "34.11-94")
	async def encode_gost_34_11_94(self, ctx, *, data : str):
		'''GOST 34.11-94 hash function'''
		await ctx.embed_reply(pygost.gost341194.GOST341194(data.encode("UTF-8")).hexdigest())
	
	@encode_gost.command(name = "34.12-2015", aliases = ["кузнечик", "kuznyechik"])
	async def encode_gost_34_12_2015(self, ctx, key : str, *, data : str):
		'''
		GOST 34.12-2015 128-bit block cipher
		Also known as Кузнечик or Kuznyechik
		key length >= 32, data length >= 16
		'''
		# TODO: Add encode kuznyechik alias
		if len(key) < 32:
			return await ctx.embed_reply(":no_entry: Error: key length must be at least 32")
		if len(data) < 16:
			return await ctx.embed_reply(":no_entry: Error: data length must be at least 16")
		await ctx.embed_reply(pygost.gost3412.GOST3412Kuznechik(key.encode("UTF-8")).encrypt(data.encode("UTF-8")).hex())
	
	@encode.command(name = "md4")
	async def encode_md4(self, ctx, *, message : str):
		'''Generate MD4 hash'''
		md4_hash = hashlib.new("MD4")
		md4_hash.update(message.encode("UTF-8"))
		await ctx.embed_reply(md4_hash.hexdigest())
	
	@encode.command(name = "md5")
	async def encode_md5(self, ctx, *, message : str):
		'''Generate MD5 hash'''
		await ctx.embed_reply(hashlib.md5(message.encode("UTF-8")).hexdigest())
	
	@encode.command(name = "morse")
	async def encode_morse(self, ctx, *, message : str):
		'''Encode a message in morse code'''
		try:
			await ctx.embed_reply(encode_morse_code(message))
		except UnitOutputError as e:
			await ctx.embed_reply(f":no_entry: Error: {e}")
	
	@encode.command(name = "qr")
	async def encode_qr(self, ctx, *, message: str):
		'''Encode a message in a QR code'''
		url = f"https://api.qrserver.com/v1/create-qr-code/?data={message.replace(' ', '+')}"
		await ctx.embed_reply(image_url = url)
	
	@encode.command(name = "reverse")
	async def encode_reverse(self, ctx, *, message : str):
		'''Reverses text'''
		await ctx.embed_reply(message[::-1])
	
	@encode.command(name = "ripemd160", aliases = ["ripemd-160"])
	async def encode_ripemd160(self, ctx, *, message : str):
		'''Generate RIPEMD-160 hash'''
		h = hashlib.new("RIPEMD160")
		h.update(message.encode("UTF-8"))
		await ctx.embed_reply(h.hexdigest())
	
	@encode.command(name = "sha1", aliases = ["sha-1"])
	async def encode_sha1(self, ctx, *, message : str):
		'''Generate SHA-1 hash'''
		await ctx.embed_reply(hashlib.sha1(message.encode("UTF-8")).hexdigest())
	
	@encode.command(name = "sha224", aliases = ["sha-224"])
	async def encode_sha224(self, ctx, *, message : str):
		'''Generate SHA-224 hash'''
		await ctx.embed_reply(hashlib.sha224(message.encode("UTF-8")).hexdigest())
	
	@encode.command(name = "sha256", aliases = ["sha-256"])
	async def encode_sha256(self, ctx, *, message : str):
		'''Generate SHA-256 hash'''
		await ctx.embed_reply(hashlib.sha256(message.encode("UTF-8")).hexdigest())
	
	@encode.command(name = "sha384", aliases = ["sha-384"])
	async def encode_sha384(self, ctx, *, message : str):
		'''Generate SHA-384 hash'''
		await ctx.embed_reply(hashlib.sha384(message.encode("UTF-8")).hexdigest())
	
	@encode.command(name = "sha512", aliases = ["sha-512"])
	async def encode_sha512(self, ctx, *, message : str):
		'''Generate SHA-512 hash'''
		await ctx.embed_reply(hashlib.sha512(message.encode("UTF-8")).hexdigest())
	
	@encode.command(name = "whirlpool")
	async def encode_whirlpool(self, ctx, *, message : str):
		'''Generate WHIRLPOOL hash'''
		h = hashlib.new("WHIRLPOOL")
		h.update(message.encode("UTF-8"))
		await ctx.embed_reply(h.hexdigest())

