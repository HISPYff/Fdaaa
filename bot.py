import asyncio
import os
import sqlite3
from html import escape

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = os.getenv("BOT_TOKEN", "PASTE_BOT_TOKEN_HERE")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
SELLER_USERNAME = os.getenv("SELLER_USERNAME", "seller_username")
DB = "catalog.db"

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = db()
    c.execute("CREATE TABLE IF NOT EXISTS categories(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL)")
    c.execute("""CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        price TEXT DEFAULT '',
        photo_id TEXT DEFAULT '',
        FOREIGN KEY(category_id) REFERENCES categories(id))""")
    c.commit(); c.close()

def categories():
    c=db(); r=c.execute("SELECT * FROM categories ORDER BY id").fetchall(); c.close(); return r

def category(cid):
    c=db(); r=c.execute("SELECT * FROM categories WHERE id=?", (cid,)).fetchone(); c.close(); return r

def products(cid):
    c=db(); r=c.execute("SELECT * FROM products WHERE category_id=? ORDER BY id", (cid,)).fetchall(); c.close(); return r

def product(pid):
    c=db(); r=c.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone(); c.close(); return r

def all_products():
    c=db(); r=c.execute("""SELECT p.*, c.name category FROM products p
                           JOIN categories c ON c.id=p.category_id
                           ORDER BY c.id,p.id""").fetchall(); c.close(); return r

def seller_url():
    return f"https://t.me/{SELLER_USERNAME.lstrip('@')}"

def home_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 Открыть каталог", callback_data="catalog")],
        [InlineKeyboardButton(text="🔎 Найти товар", callback_data="search")],
        [InlineKeyboardButton(text="📞 Связаться с продавцом", url=seller_url())]
    ])

def cats_kb():
    b=[[InlineKeyboardButton(text=f"▸ {x['name']}", callback_data=f"cat:{x['id']}")] for x in categories()]
    b += [
        [InlineKeyboardButton(text="🔎 Поиск", callback_data="search")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="home")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=b)

def products_kb(cid, items):
    b=[]
    for p in items:
        label=f"🔧 {p['name']}"
        if p["price"]: label += f" · {p['price']}"
        b.append([InlineKeyboardButton(text=label[:60], callback_data=f"prod:{p['id']}:0")])
    b += [
        [InlineKeyboardButton(text="⬅️ Разделы", callback_data="catalog")],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="home")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=b)

def nav_kb(items, index, cid):
    pid=items[index]["id"]
    row=[]
    if index>0: row.append(InlineKeyboardButton(text="◀️ Предыдущий", callback_data=f"prod:{pid}:prev"))
    if index<len(items)-1: row.append(InlineKeyboardButton(text="Следующий ▶️", callback_data=f"prod:{pid}:next"))
    b=[row] if row else []
    b += [
        [InlineKeyboardButton(text="📞 Написать продавцу", url=seller_url())],
        [InlineKeyboardButton(text="⬅️ К товарам", callback_data=f"cat:{cid}")],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="home")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=b)

bot=Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp=Dispatcher(storage=MemoryStorage())

async def render_product(target, pid, index_hint=0, edit=False):
    p=product(pid)
    if not p: return
    items=products(p["category_id"])
    idx=next((i for i,x in enumerate(items) if x["id"]==pid),0)
    text=f"🔧 <b>{escape(p['name'])}</b>\n\n"
    if p["description"]: text += escape(p["description"])+"\n\n"
    if p["price"]: text += f"💰 <b>{escape(p['price'])}</b>\n"
    text += f"\n📦 Раздел: {escape(category(p['category_id'])['name'])}\n"
    text += f"📄 Товар {idx+1} из {len(items)}"
    kb=nav_kb(items,idx,p["category_id"])

    if edit and not p["photo_id"]:
        await target.edit_text(text, reply_markup=kb)
    else:
        if p["photo_id"]:
            await target.answer_photo(p["photo_id"], caption=text, reply_markup=kb)
        else:
            await target.answer(text, reply_markup=kb)

@dp.message(CommandStart())
async def start(m:Message):
    await m.answer(
        "⚡ <b>КУРЬЕРСКИЕ ДВИЖЕНИЯ</b>\n\n"
        "Комплектующие для электровелосипедов.\n"
        "Выберите раздел или найдите нужную деталь:",
        reply_markup=home_kb())

@dp.callback_query(F.data == "home")
async def home(c: CallbackQuery):
    try:
        await c.message.edit_text(
            "⚡ <b>КУРЬЕРСКИЕ ДВИЖЕНИЯ</b>\n\nВыберите действие:",
            reply_markup=home_kb()
        )
    except Exception:
        await c.message.delete()
        await c.message.answer(
            "⚡ <b>КУРЬЕРСКИЕ ДВИЖЕНИЯ</b>\n\nВыберите действие:",
            reply_markup=home_kb()
        )

    await c.answer()

@dp.callback_query(F.data.startswith("cat:"))
async def cat(c: CallbackQuery):
    cid = int(c.data.split(":")[1])
    x = category(cid)

    if not x:
        return await c.answer("Раздел не найден", show_alert=True)

    ps = products(cid)

    text = f"📂 <b>{escape(x['name'])}</b>\n\n"
    text += f"Найдено товаров: <b>{len(ps)}</b>\n\n"
    text += "Выберите товар:"

    try:
        await c.message.edit_text(
            text,
            reply_markup=products_kb(cid, ps)
        )
    except Exception:
        await c.message.delete()
        await c.message.answer(
            text,
            reply_markup=products_kb(cid, ps)
        )

    await c.answer()

@dp.callback_query(F.data.startswith("prod:"))
async def prod(c:CallbackQuery):
    _,pid,action=c.data.split(":"); pid=int(pid)
    p=product(pid)
    if not p: return await c.answer("Товар не найден", show_alert=True)
    items=products(p["category_id"])
    idx=next(i for i,x in enumerate(items) if x["id"]==pid)
    if action=="next" and idx<len(items)-1: pid=items[idx+1]["id"]
    elif action=="prev" and idx>0: pid=items[idx-1]["id"]
    p=product(pid)
    items=products(p["category_id"]); idx=next(i for i,x in enumerate(items) if x["id"]==pid)
    text=f"🔧 <b>{escape(p['name'])}</b>\n\n"
    if p["description"]: text += escape(p["description"])+"\n\n"
    if p["price"]: text += f"💰 <b>{escape(p['price'])}</b>\n"
    text += f"\n📦 {escape(category(p['category_id'])['name'])}\n"
    text += f"📄 {idx+1} / {len(items)}"
    kb=nav_kb(items,idx,p["category_id"])
    if p["photo_id"]:
        await c.message.delete()
        await c.message.answer_photo(p["photo_id"], caption=text, reply_markup=kb)
    else:
        await c.message.edit_text(text, reply_markup=kb)
    await c.answer()

@dp.callback_query(F.data=="search")
async def search_button(c:CallbackQuery, state:FSMContext):
    await state.set_state(SearchState.query)
    await c.message.answer("🔎 <b>Поиск товара</b>\n\nВведите название или часть названия:")
    await c.answer()

class SearchState(StatesGroup):
    query=State()

@dp.message(SearchState.query)
async def search(m:Message,state:FSMContext):
    q=m.text.strip().lower()
    rows=[p for p in all_products() if q in p["name"].lower() or q in (p["description"] or "").lower() or q in p["category"].lower()]
    await state.clear()
    if not rows:
        await m.answer("😕 Ничего не найдено.\nПопробуйте другое название.", reply_markup=home_kb()); return
    b=[]
    for p in rows:
        label=f"🔧 {p['name']}"
        if p["price"]: label+=f" · {p['price']}"
        b.append([InlineKeyboardButton(text=label[:60],callback_data=f"prod:{p['id']}:0")])
    b.append([InlineKeyboardButton(text="🏠 Главное меню",callback_data="home")])
    await m.answer(f"🔎 <b>Результаты поиска:</b> {len(rows)}", reply_markup=InlineKeyboardMarkup(inline_keyboard=b))

# ----- Admin -----
def is_admin(m): return ADMIN_ID and m.from_user.id==ADMIN_ID
class AddCategory(StatesGroup): name=State()
class AddProduct(StatesGroup):
    category=State(); name=State(); description=State(); price=State(); photo=State()

@dp.message(Command("admin"))
async def admin(m:Message):
    if not is_admin(m): return
    await m.answer("<b>⚙️ Админ-панель</b>\n\n/addcat\n/addproduct\n/cats\n/products\n/delcat ID\n/delproduct ID")

@dp.message(Command("addcat"))
async def addcat(m: Message, state: FSMContext):
    if not is_admin(m): return
    await state.set_state(AddCategory.name)
    await m.answer("Название нового раздела:")

@dp.message(AddCategory.name)
async def addcat_name(m: Message, state: FSMContext):
    if not is_admin(m):
        return

    c = db()
    c.execute(
        "INSERT INTO categories(name) VALUES(?)",
        (m.text.strip(),)
    )
    c.commit()
    c.close()

    await state.clear()
    await m.answer("✅ Раздел добавлен.")

@dp.message(Command("addproduct"))
async def addproduct(m: Message, state: FSMContext):
    if not is_admin(m):
        return

    cs = categories()
    if not cs:
        return await m.answer("Сначала добавьте раздел /addcat")

    await state.set_state(AddProduct.category)
    await m.answer(
        "ID раздела:\n" +
        "\n".join(f"{x['id']} — {x['name']}" for x in cs)
    )

@dp.message(AddProduct.category)
async def pc(m: Message, state: FSMContext):
    if not is_admin(m):
        return

    try:
        cid = int(m.text)
    except:
        return await m.answer("Введите число.")

    if not category(cid):
        return await m.answer("Такого раздела нет.")

    await state.update_data(category=cid)
    await state.set_state(AddProduct.name)
    await m.answer("Название товара:")

@dp.message(AddProduct.name)
async def pn(m: Message, state: FSMContext):
    await state.update_data(name=m.text.strip())
    await state.set_state(AddProduct.description)
    await m.answer("Описание (или -):")

@dp.message(AddProduct.description)
async def pd(m: Message, state: FSMContext):
    description = "" if m.text.strip() == "-" else m.text.strip()
    await state.update_data(description=description)
    await state.set_state(AddProduct.price)
    await m.answer("Цена (или -):")

@dp.message(AddProduct.price)
async def pp(m: Message, state: FSMContext):
    price = "" if m.text.strip() == "-" else m.text.strip()
    await state.update_data(price=price)
    await state.set_state(AddProduct.photo)
    await m.answer("Фото товара или -:")


@dp.message(AddProduct.photo)
async def pphoto(m: Message, state: FSMContext):
    d = await state.get_data()

    if m.photo:
        photo = m.photo[-1].file_id
    elif m.text and m.text.strip() == "-":
        photo = ""
    else:
        return await m.answer("Отправьте фото или -.")

    c = db()
    c.execute(
        "INSERT INTO products(category_id,name,description,price,photo_id) VALUES(?,?,?,?,?)",
        (
            d["category"],
            d["name"],
            d["description"],
            d["price"],
            photo
        )
    )
    c.commit()
    c.close()

    await state.clear()
    await m.answer("✅ Товар добавлен.")

@dp.message(Command("cats"))
async def cats(m:Message):
    if not is_admin(m): return
    await m.answer("\n".join(f"{x['id']} — {x['name']}" for x in categories()) or "Нет разделов.")

@dp.message(Command("products"))
async def plist(m:Message):
    if not is_admin(m): return
    await m.answer("\n".join(f"{x['id']} — {x['name']} [{x['category']}]" for x in all_products()) or "Нет товаров.")

@dp.message(Command("delproduct"))
async def delp(m:Message):
    if not is_admin(m): return
    parts=m.text.split()
    if len(parts)!=2: return await m.answer("/delproduct ID")
    c=db(); c.execute("DELETE FROM products WHERE id=?",(int(parts[1]),)); c.commit(); c.close()
    await m.answer("✅ Товар удалён.")

@dp.message(Command("delcat"))
async def delc(m:Message):
    if not is_admin(m): return
    parts=m.text.split()
    if len(parts)!=2: return await m.answer("/delcat ID")
    cid=int(parts[1]); c=db()
    c.execute("DELETE FROM products WHERE category_id=?",(cid,)); c.execute("DELETE FROM categories WHERE id=?",(cid,))
    c.commit(); c.close(); await m.answer("✅ Раздел удалён.")

async def main():
    init_db()
    if TOKEN=="PASTE_BOT_TOKEN_HERE": raise RuntimeError("Укажите BOT_TOKEN.")
    await dp.start_polling(bot)

if __name__=="__main__":
    asyncio.run(main())
