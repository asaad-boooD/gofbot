import os
import random
import string
import threading
import requests
import io
import time
import json
from datetime import datetime
from flask import Flask, request, render_template_string, session, redirect, url_for, Response, jsonify

app = Flask(__name__)
app.secret_key = "As3ad_Enterprise_Secret_2024"

SETTINGS_FILE = "settings.json"
CHECKED_FILE = "checked_history.txt"
VALID_FILE = "valid_history.txt"
MESSAGED_FILE = "messaged_history.txt"
GENERATED_FILE = "generated_history.txt"
CURRENT_BATCH_FILE = "current_batch.txt"

current_status = "idle"
logs = []
generated_numbers = []
valid_numbers = []
stats = {"total": 0, "valid": 0, "invalid": 0}

COUNTRIES = {
    "Kuwait": {"code": "+965", "length": 8, "prefixes": ["5", "6", "9"], "ar": "الكويت", "flag": "🇰🇼"},
    "Saudi Arabia": {"code": "+966", "length": 9, "prefixes": ["5"], "ar": "السعودية", "flag": "🇸🇦"},
    "UAE": {"code": "+971", "length": 9, "prefixes": ["5"], "ar": "الإمارات", "flag": "🇦🇪"},
    "Qatar": {"code": "+974", "length": 8, "prefixes": ["3", "5", "6", "7"], "ar": "قطر", "flag": "🇶🇦"},
    "Bahrain": {"code": "+973", "length": 8, "prefixes": ["3"], "ar": "البحرين", "flag": "🇧🇭"},
    "Oman": {"code": "+968", "length": 8, "prefixes": ["7", "9"], "ar": "عمان", "flag": "🇴🇲"},
}

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_settings(data):
    current = load_settings()
    current.update(data)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f)

def get_apify_token():
    return load_settings().get("APIFY_TOKEN") or os.environ.get("APIFY_API_TOKEN", "")

def load_set(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def load_list(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    return []

def append_to_file(filename, items):
    with open(filename, "a", encoding="utf-8") as f:
        for item in items:
            f.write(item + "\n")

def save_current_batch(numbers):
    with open(CURRENT_BATCH_FILE, "w", encoding="utf-8") as f:
        for n in numbers:
            f.write(n + "\n")

def get_country_from_number(number):
    for country, data in COUNTRIES.items():
        if number.startswith(data["code"]):
            return country
    return "Unknown"

def generate_vcf(valid_numbers_set):
    lines = []
    for i, number in enumerate(sorted(valid_numbers_set), start=1):
        clean = number.strip().replace(" ", "").replace("-", "")
        if not clean.startswith("+"):
            clean = "+" + clean
        country_name = get_country_from_number(clean)
        contact_name = f"WA-{i}"
        lines.append("BEGIN:VCARD")
        lines.append("VERSION:3.0")
        lines.append(f"FN:{contact_name}")
        lines.append(f"N:{contact_name};;;;")
        lines.append(f"TEL;TYPE=CELL,VOICE:{clean}")
        lines.append(f"NOTE:Country: {country_name} | Validated via As3ad Platform on {datetime.now().strftime('%Y-%m-%d')}")
        lines.append("END:VCARD")
    return "\r\n".join(lines) + "\r\n"

# ========== التعلم الذكي ==========
def extract_learned_blocks(country, block_length=3):
    """استخراج البادئات الحقيقية من الأرقام الصحيحة المسجلة لهذه الدولة"""
    valid = load_set(VALID_FILE)
    code = COUNTRIES[country]["code"]
    length = COUNTRIES[country]["length"]
    
    blocks = {}
    for num in valid:
        if num.startswith(code):
            rest = num[len(code):]
            b_len = min(block_length, length)
            if len(rest) >= b_len:
                block = rest[:b_len]
                blocks[block] = blocks.get(block, 0) + 1
    return blocks

def get_learning_summary():
    """ملخص التعلم لكل دولة - للعرض في الواجهة"""
    summary = {}
    for country in COUNTRIES.keys():
        blocks = extract_learned_blocks(country, block_length=3)
        total = sum(blocks.values())
        summary[country] = {
            "name_ar": COUNTRIES[country]["ar"],
            "flag": COUNTRIES[country]["flag"],
            "total_valid": total,
            "blocks": blocks,
            "top_block": max(blocks, key=blocks.get) if blocks else None,
            "prefix_count": len(blocks)
        }
    return summary

# ========== قوالب HTML ==========
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8"><title>As3ad Platform | Login</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap" rel="stylesheet">
    <style>
        :root { --bg: #050810; --panel: rgba(15, 23, 42, 0.8); --primary: #00f0ff; --text: #e2e8f0; --muted: #64748b; --danger: #f43f5e; --border: rgba(0, 240, 255, 0.2); }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Cairo', sans-serif; }
        body { background: var(--bg); color: var(--text); display: flex; justify-content: center; align-items: center; height: 100vh; overflow: hidden; background-image: radial-gradient(circle at 10% 20%, rgba(0, 240, 255, 0.15) 0%, transparent 40%), radial-gradient(circle at 90% 80%, rgba(16, 185, 129, 0.1) 0%, transparent 40%); }
        .login-box { background: var(--panel); backdrop-filter: blur(20px); padding: 50px 40px; border-radius: 24px; box-shadow: 0 30px 60px rgba(0,0,0,0.6), inset 0 0 0 1px var(--border); width: 100%; max-width: 420px; text-align: center; }
        .logo-icon { font-size: 48px; margin-bottom: 15px; display: inline-block; filter: drop-shadow(0 0 10px var(--primary)); }
        h2 { margin-bottom: 10px; font-weight: 900; font-size: 28px; }
        p.subtitle { color: var(--muted); margin-bottom: 35px; font-size: 15px; }
        .input-group { margin-bottom: 20px; text-align: right; }
        label { display: block; margin-bottom: 8px; font-size: 14px; color: #94a3b8; font-weight: 700; }
        input { width: 100%; padding: 16px; background: rgba(0,0,0,0.3); border: 1px solid #334155; border-radius: 12px; color: white; outline: none; font-family: 'Cairo'; font-size: 15px; }
        input:focus { border-color: var(--primary); }
        button { width: 100%; padding: 16px; background: var(--primary); color: #000; border: none; border-radius: 12px; font-size: 16px; font-weight: 900; cursor: pointer; margin-top: 10px; font-family: 'Cairo'; }
        .error { color: var(--danger); background: rgba(244, 63, 94, 0.1); padding: 12px; border-radius: 8px; margin-bottom: 20px; font-weight: 700; border: 1px solid rgba(244, 63, 94, 0.3); }
    </style>
</head>
<body>
    <div class="login-box">
        <div class="logo-icon">⚡</div>
        <h2>As3ad Platform</h2>
        <p class="subtitle">منصة الخدمات الذكية المتكاملة</p>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="POST">
            <div class="input-group"><label>اسم المستخدم</label><input type="text" name="username" required autocomplete="off"></div>
            <div class="input-group"><label>كلمة المرور</label><input type="password" name="password" required></div>
            <button type="submit">تسجيل الدخول</button>
        </form>
    </div>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8"><title>As3ad Platform | Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap" rel="stylesheet">
    <style>
        :root { --bg: #050810; --panel: #0f172a; --panel-light: #1e293b; --primary: #00f0ff; --success: #10b981; --danger: #f43f5e; --warning: #f59e0b; --text: #e2e8f0; --muted: #64748b; --border: #1e293b; }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Cairo', sans-serif; }
        body { background: var(--bg); color: var(--text); display: flex; height: 100vh; overflow: hidden; }
        .sidebar { width: 280px; background: var(--panel); border-left: 1px solid var(--border); display: flex; flex-direction: column; }
        .brand { padding: 30px 20px; font-size: 24px; font-weight: 900; display: flex; align-items: center; gap: 10px; border-bottom: 1px solid var(--border); }
        .brand-icon { color: var(--primary); font-size: 28px; filter: drop-shadow(0 0 8px var(--primary)); }
        .nav-menu { padding: 20px 15px; flex: 1; display: flex; flex-direction: column; gap: 10px; }
        .nav-item { padding: 16px 20px; border-radius: 12px; cursor: pointer; display: flex; align-items: center; gap: 15px; font-weight: 700; color: var(--muted); transition: all 0.3s; border: 1px solid transparent; }
        .nav-item:hover { background: rgba(0, 240, 255, 0.05); color: var(--text); }
        .nav-item.active { background: rgba(0, 240, 255, 0.1); color: var(--primary); border: 1px solid rgba(0, 240, 255, 0.2); }
        .logout-btn { padding: 20px; border-top: 1px solid var(--border); color: var(--danger); text-decoration: none; font-weight: 900; display: flex; justify-content: center; }
        .main-content { flex: 1; overflow-y: auto; padding: 40px; display: none; }
        .main-content.active { display: block; }
        .header-title { font-size: 28px; font-weight: 900; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: var(--panel-light); border: 1px solid var(--border); border-radius: 16px; padding: 22px; display: flex; align-items: center; gap: 15px; }
        .stat-icon { width: 60px; height: 60px; border-radius: 16px; display: flex; justify-content: center; align-items: center; font-size: 26px; flex-shrink: 0; }
        .stat-icon.total { background: rgba(0, 240, 255, 0.1); color: var(--primary); }
        .stat-icon.valid { background: rgba(16, 185, 129, 0.1); color: var(--success); }
        .stat-icon.invalid { background: rgba(244, 63, 94, 0.1); color: var(--danger); }
        .stat-icon.generated { background: rgba(245, 158, 11, 0.1); color: var(--warning); }
        .stat-info h4 { color: var(--muted); font-size: 13px; margin-bottom: 6px; }
        .stat-info span { font-size: 28px; font-weight: 900; }
        .content-grid { display: grid; grid-template-columns: 380px 1fr; gap: 25px; }
        .panel { background: var(--panel); border: 1px solid var(--border); border-radius: 20px; padding: 28px; margin-bottom: 25px; }
        .panel-title { font-size: 19px; font-weight: 900; margin-bottom: 22px; padding-bottom: 14px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
        .form-group { margin-bottom: 18px; }
        label { display: block; margin-bottom: 10px; font-size: 14px; color: var(--muted); font-weight: 700; }
        select, input, textarea { width: 100%; padding: 13px; background: rgba(0,0,0,0.3); border: 1px solid #334155; border-radius: 12px; color: white; outline: none; font-family: 'Cairo'; font-size: 15px; }
        .btn { width: 100%; padding: 15px; border: none; border-radius: 12px; font-weight: 900; cursor: pointer; font-family: 'Cairo'; font-size: 15px; display: flex; justify-content: center; align-items: center; gap: 10px; margin-top: 10px; transition: 0.3s; }
        .btn-primary { background: var(--primary); color: #000; }
        .btn-primary:hover { box-shadow: 0 0 20px rgba(0, 240, 255, 0.4); }
        .btn-success { background: var(--success); color: white; }
        .btn-success:hover { box-shadow: 0 0 20px rgba(16, 185, 129, 0.4); }
        .btn-warning { background: var(--warning); color: #000; }
        .btn-warning:hover { box-shadow: 0 0 20px rgba(245, 158, 11, 0.4); }
        .btn-danger { background: rgba(244, 63, 94, 0.1); color: var(--danger); border: 1px solid var(--danger); }
        .btn-danger:hover { background: var(--danger); color: white; }
        .btn:disabled { background: #1e293b; color: var(--muted); cursor: not-allowed; box-shadow: none; }
        .terminal-panel { background: #000; border: 1px solid var(--border); border-radius: 20px; display: flex; flex-direction: column; height: 550px; overflow: hidden; }
        .terminal-header { background: var(--panel-light); padding: 14px 18px; display: flex; align-items: center; gap: 8px; border-bottom: 1px solid var(--border); }
        .dot { width: 12px; height: 12px; border-radius: 50%; }
        .dot.red { background: #ef4444; } .dot.yellow { background: #f59e0b; } .dot.green { background: #10b981; }
        .terminal-title { margin-right: auto; font-size: 13px; color: var(--muted); font-family: monospace; font-weight: bold; }
        .terminal-body { padding: 18px; flex: 1; overflow-y: auto; font-family: 'Consolas', monospace; font-size: 13px; line-height: 1.6; direction: ltr; text-align: left; }
        .log-line { margin-bottom: 5px; padding: 4px 8px; border-radius: 4px; }
        .log-info { color: var(--primary); background: rgba(0, 240, 255, 0.05); }
        .log-success { color: var(--success); background: rgba(16, 185, 129, 0.05); border-left: 3px solid var(--success); }
        .log-error { color: var(--danger); background: rgba(244, 63, 94, 0.05); border-left: 3px solid var(--danger); }
        .log-warn { color: #f59e0b; background: rgba(245, 158, 11, 0.05); border-left: 3px solid #f59e0b; }
        .export-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .export-card { background: var(--panel); border: 1px solid var(--border); border-radius: 16px; padding: 25px; }
        .export-card h4 { font-size: 18px; margin-bottom: 10px; color: var(--primary); }
        .export-card p { color: var(--muted); font-size: 13px; margin-bottom: 15px; line-height: 1.6; }
        .batch-list { max-height: 220px; overflow-y: auto; font-family: 'Consolas', monospace; font-size: 13px; direction: ltr; text-align: left; color: var(--text); line-height: 1.8; background: rgba(0,0,0,0.3); border-radius: 10px; padding: 12px; border: 1px solid var(--border); }
        .batch-list::-webkit-scrollbar { width: 8px; }
        .batch-list::-webkit-scrollbar-thumb { background: var(--primary); border-radius: 4px; }
        .batch-empty { color: var(--muted); text-align: center; padding: 25px; font-family: 'Cairo'; }
        .badge { display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 700; }
        .badge-primary { background: rgba(0, 240, 255, 0.1); color: var(--primary); border: 1px solid rgba(0,240,255,0.3); }
        .badge-success { background: rgba(16, 185, 129, 0.15); color: var(--success); border: 1px solid rgba(16,185,129,0.3); margin: 2px; }
        .badge-warning { background: rgba(245, 158, 11, 0.15); color: var(--warning); border: 1px solid rgba(245,158,11,0.3); }
        .learn-card { margin-bottom: 15px; padding: 15px; background: rgba(0,0,0,0.2); border-radius: 12px; border: 1px solid var(--border); }
        .learn-header { font-weight: 900; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
        .learn-blocks { display: flex; flex-wrap: wrap; gap: 6px; }
        .learn-block-tag { background: rgba(16, 185, 129, 0.15); color: var(--success); border: 1px solid rgba(16,185,129,0.3); padding: 4px 10px; border-radius: 20px; font-size: 13px; font-weight: 700; font-family: 'Consolas', monospace; }
        .learn-block-tag .freq { color: var(--warning); margin-right: 5px; font-weight: 900; }
        .info-note { font-size: 12px; color: var(--muted); margin-top: 10px; line-height: 1.6; padding: 10px; background: rgba(0, 240, 255, 0.03); border-right: 3px solid var(--primary); border-radius: 6px; }
        @media (max-width: 1024px) { .content-grid { grid-template-columns: 1fr; } .export-grid { grid-template-columns: 1fr; } }
        @media (max-width: 768px) {
            body { flex-direction: column; }
            .sidebar { width: 100%; flex-direction: row; align-items: center; padding: 0 10px; height: 70px; border-left: none; border-bottom: 1px solid var(--border); overflow-x: auto; }
            .brand { padding: 10px; font-size: 20px; border-bottom: none; display: none; }
            .nav-menu { flex-direction: row; padding: 0; gap: 5px; }
            .nav-item { padding: 10px; font-size: 13px; white-space: nowrap; }
            .logout-btn { padding: 10px; border-top: none; font-size: 14px; white-space: nowrap; }
            .main-content { padding: 20px; }
        }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="brand"><span class="brand-icon">⚡</span> As3ad</div>
        <div class="nav-menu">
            <div class="nav-item active" id="nav-wa" onclick="switchTab('wa')">📱 فاحص واتساب</div>
            <div class="nav-item" id="nav-export" onclick="switchTab('export')">📤 تصدير الأرقام</div>
            <div class="nav-item" id="nav-settings" onclick="switchTab('settings')">⚙️ الإعدادات</div>
        </div>
        <a href="/logout" class="logout-btn">تسجيل خروج</a>
    </div>

    <div class="main-content active" id="wa-section">
        <div class="header-title">
            <span>منصة فحص أرقام الواتساب</span>
            <button onclick="resetHistory()" class="btn btn-danger" style="width: auto; padding: 10px 20px; margin: 0; font-size: 14px;">🗑️ مسح كل السجلات</button>
        </div>

        <div class="stats-grid">
            <div class="stat-card"><div class="stat-icon total">📊</div><div class="stat-info"><h4>المفحوصة (الجلسة)</h4><span id="statTotal">0</span></div></div>
            <div class="stat-card"><div class="stat-icon valid">✅</div><div class="stat-info"><h4>مسجلة واتساب</h4><span id="statValid">0</span></div></div>
            <div class="stat-card"><div class="stat-icon invalid">❌</div><div class="stat-info"><h4>غير مسجلة</h4><span id="statInvalid">0</span></div></div>
            <div class="stat-card"><div class="stat-icon generated">⚡</div><div class="stat-info"><h4>إجمالي المولدة</h4><span id="statGenerated">0</span></div></div>
        </div>

        <div class="content-grid">
            <div class="panel">
                <div class="panel-title">⚙️ لوحة التحكم</div>
                <div class="form-group">
                    <label>1. اختر الدولة المستهدفة</label>
                    <select id="country">
                        {% for name in countries %}<option value="{{ name }}">{{ countries[name].flag }} {{ countries[name].ar }} ({{ countries[name].code }})</option>{% endfor %}
                    </select>
                </div>
                <div class="form-group">
                    <label>2. عدد الأرقام المطلوب توليدها</label>
                    <input type="number" id="count" value="50" min="1" max="1000">
                </div>
                <button class="btn btn-primary" onclick="generateNumbers()" id="genBtn">🧠 توليد ذكي (يتعلم من الصحيحة)</button>
                <div class="info-note">
                    💡 <strong>التوليد الذكي:</strong> يركّز 70% من الأرقام على البادئات الحقيقية المكتشفة من الأرقام الصحيحة سابقاً، و30% استكشاف عشوائي لاكتشاف بادئات جديدة.
                </div>
                <hr style="border-color: var(--border); margin: 20px 0;">
                <div class="form-group">
                    <label>أو افحص رقماً محدداً يدوياً</label>
                    <input type="text" id="specific" placeholder="+965xxxxxxxx">
                </div>
                <button class="btn btn-success" onclick="startChecking()" id="checkBtn" disabled>🚀 بدء الفحص</button>
            </div>
            <div class="terminal-panel">
                <div class="terminal-header"><div class="dot red"></div><div class="dot yellow"></div><div class="dot green"></div><span class="terminal-title">as3ad@validator: ~/logs</span></div>
                <div class="terminal-body" id="logsBox"><div class="log-line log-info">> System initialized. Ready for commands...</div></div>
            </div>
        </div>

        <!-- لوحة التعلم الذكي -->
        <div class="panel">
            <div class="panel-title">
                🧠 البادئات المتعلَّمة من الأرقام الصحيحة
                <span class="badge badge-primary" style="margin-right: auto;">يتم تحديثها تلقائياً</span>
            </div>
            <p style="color: var(--muted); font-size: 13px; margin-bottom: 15px; line-height: 1.6;">
                هذه هي البادئات (أول 3 أرقام) التي تم استخراجها من أرقامك الصحيحة. كلما زاد عدد الأرقام الصحيحة، زادت دقة التوليد القادم. التوليد القادم سيركّز 70% على هذه البادئات.
            </p>
            <div id="learnedBlocksContainer">
                <div class="batch-empty">لا توجد بيانات تعلم بعد — قم بتوليد وفحص أرقام أولاً</div>
            </div>
        </div>

        <!-- لوحة الأرقام المولدة الحالية -->
        <div class="panel">
            <div class="panel-title">
                📋 الأرقام المولدة الحالية
                <span class="badge badge-primary" style="margin-right: auto;"><span id="currentBatchCount">0</span> رقم</span>
            </div>
            <div id="currentBatchList" class="batch-list">
                <div class="batch-empty">لا توجد أرقام مولدة حالياً — اضغط "توليد ذكي"</div>
            </div>
            <button class="btn btn-warning" onclick="downloadCurrent()" style="margin-top: 15px;">⬇️ تحميل الدفعة الحالية (TXT)</button>
        </div>
    </div>

    <div class="main-content" id="export-section">
        <div class="header-title">تصدير جهات الاتصال</div>
        <div class="export-grid">
            <div class="export-card">
                <h4>📇 استيراد كجهات اتصال (VCF)</h4>
                <p>حمّل الأرقام كملف VCF لاستيرادها مباشرة إلى جهات اتصال هاتفك. الأسماء تصاعدية (WA-1, WA-2, ...).</p>
                <button onclick="downloadVCF()" class="btn btn-primary" style="margin-top: 15px;">⬇️ تحميل ملف VCF</button>
            </div>
            <div class="export-card">
                <h4>📄 تحميل كملف نصي (TXT)</h4>
                <p>حمّل الأرقام الصحيحة فقط كملف نصي بسيط بصيغة دولية.</p>
                <button onclick="downloadTXT()" class="btn btn-warning" style="margin-top: 15px;">⬇️ تحميل ملف TXT</button>
            </div>
        </div>
    </div>

    <div class="main-content" id="settings-section">
        <div class="header-title">إعدادات المنصة</div>
        <div class="panel" style="max-width: 600px; margin: 0 auto;">
            <div class="panel-title">🔑 مفاتيح API</div>
            <div class="form-group">
                <label>Apify API Token</label>
                <input type="text" id="apifyTokenInput" placeholder="apify_api_..." value="{{ apify_token }}">
            </div>
            <button class="btn btn-primary" onclick="saveSettings()" id="saveBtn">💾 حفظ المفاتيح</button>
        </div>
    </div>

    <script>
        let pollingInterval = null;

        function switchTab(tab) {
            document.querySelectorAll('.main-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
            if(tab === 'wa') { document.getElementById('wa-section').classList.add('active'); document.getElementById('nav-wa').classList.add('active'); }
            else if(tab === 'export') { document.getElementById('export-section').classList.add('active'); document.getElementById('nav-export').classList.add('active'); }
            else if(tab === 'settings') { document.getElementById('settings-section').classList.add('active'); document.getElementById('nav-settings').classList.add('active'); }
        }

        async function loadLearnedBlocks() {
            try {
                const res = await fetch('/api/learned-blocks');
                const data = await res.json();
                let html = '';
                for (const [country, info] of Object.entries(data)) {
                    if (info.total_valid === 0) continue;
                    const entries = Object.entries(info.blocks).sort((a, b) => b[1] - a[1]);
                    html += `<div class="learn-card">
                        <div class="learn-header">
                            <span>${info.flag} ${info.name_ar}</span>
                            <span class="badge badge-success">${info.total_valid} رقم صحيح / ${info.prefix_count} بادئة</span>
                        </div>
                        <div class="learn-blocks">`;
                    for (const [block, freq] of entries) {
                        html += `<span class="learn-block-tag"><span class="freq">×${freq}</span>${block}</span>`;
                    }
                    html += `</div></div>`;
                }
                if (!html) {
                    html = '<div class="batch-empty">لا توجد بيانات تعلم بعد — قم بتوليد وفحص أرقام أولاً</div>';
                }
                document.getElementById('learnedBlocksContainer').innerHTML = html;
            } catch(e) { console.error('loadLearnedBlocks failed', e); }
        }

        async function loadCurrentBatch() {
            try {
                const res = await fetch('/api/current-batch');
                const data = await res.json();
                document.getElementById('currentBatchCount').innerText = data.numbers.length;
                const list = document.getElementById('currentBatchList');
                if (data.numbers.length === 0) {
                    list.innerHTML = '<div class="batch-empty">لا توجد أرقام مولدة حالياً — اضغط "توليد ذكي"</div>';
                    document.getElementById('checkBtn').disabled = true;
                } else {
                    list.innerHTML = data.numbers.map(n => `<div>${n}</div>`).join('');
                    document.getElementById('checkBtn').disabled = false;
                }
            } catch(e) {}
        }

        async function loadInitialStats() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                if (data.total_generated !== undefined) document.getElementById('statGenerated').innerText = data.total_generated;
                if (data.stats) {
                    document.getElementById('statTotal').innerText = data.stats.total;
                    document.getElementById('statValid').innerText = data.stats.valid;
                    document.getElementById('statInvalid').innerText = data.stats.invalid;
                }
                await loadCurrentBatch();
                await loadLearnedBlocks();
            } catch(e) {}
        }

        async function saveSettings() {
            const btn = document.getElementById('saveBtn');
            btn.disabled = true; btn.innerHTML = '⏳ جاري الحفظ...';
            const res = await fetch('/api/save-settings', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ apify_token: document.getElementById('apifyTokenInput').value }) });
            alert(res.ok ? "تم الحفظ." : "خطأ.");
            btn.disabled = false; btn.innerHTML = '💾 حفظ المفاتيح';
        }

        async function resetHistory() {
            if (!confirm("سيتم مسح كل السجلات (المولدة، المفحوصة، الصحيحة، البادئات المتعلَّمة). متأكد؟")) return;
            const res = await fetch('/api/reset-history', { method: 'POST' });
            if (res.ok) { alert("تم المسح."); location.reload(); }
        }

        async function generateNumbers() {
            const btn = document.getElementById('genBtn');
            btn.disabled = true; btn.innerHTML = '🧠 جاري التوليد الذكي...';
            try {
                const res = await fetch('/api/generate', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ country: document.getElementById('country').value, count: document.getElementById('count').value }) });
                const data = await res.json();
                addLog(`[+] تم توليد ${data.count} رقم (التعلم: ${data.learned_blocks_count || 0} بادئة نشطة).`, 'log-success');
                if (data.learned_blocks_count > 0) {
                    addLog(`    🧠 ${Math.round(data.learned_ratio * 100)}% من الأرقام في بادئات متعلَّمة + ${Math.round((1-data.learned_ratio)*100)}% استكشاف`, 'log-info');
                } else {
                    addLog(`    ⚠️ لا توجد بادئات متعلَّمة بعد — تم استخدام البادئات الأساسية`, 'log-warn');
                }
                if (data.preview && data.preview.length > 0) addLog(`    أمثلة: ${data.preview.join(', ')}`, 'log-info');
                document.getElementById('statGenerated').innerText = data.total;
                await loadCurrentBatch();
                await loadLearnedBlocks();
            } catch(e) {
                addLog('❌ فشل التوليد: ' + e.message, 'log-error');
            }
            btn.disabled = false; btn.innerHTML = '🧠 توليد ذكي (يتعلم من الصحيحة)';
        }

        async function startChecking() {
            const btn = document.getElementById('checkBtn');
            btn.disabled = true; btn.innerHTML = '⏳ جاري الفحص...';
            document.getElementById('logsBox').innerHTML = '';
            document.getElementById('statTotal').innerText = '0';
            document.getElementById('statValid').innerText = '0';
            document.getElementById('statInvalid').innerText = '0';
            const res = await fetch('/api/check', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ specific: document.getElementById('specific').value }) });
            if (res.ok && !pollingInterval) pollingInterval = setInterval(pollStatus, 1500);
        }

        async function pollStatus() {
            const res = await fetch('/api/status');
            const data = await res.json();
            if (data.stats) {
                document.getElementById('statTotal').innerText = data.stats.total;
                document.getElementById('statValid').innerText = data.stats.valid;
                document.getElementById('statInvalid').innerText = data.stats.invalid;
            }
            if (data.total_generated !== undefined) document.getElementById('statGenerated').innerText = data.total_generated;
            if (data.logs.length > 0) {
                const box = document.getElementById('logsBox'); box.innerHTML = '';
                data.logs.forEach(log => {
                    let cls = 'log-info';
                    if (log.includes('✅')) cls = 'log-success';
                    if (log.includes('❌')) cls = 'log-error';
                    if (log.includes('⚠️')) cls = 'log-warn';
                    addLog(log, cls, false);
                });
                box.scrollTop = box.scrollHeight;
            }
            if (data.status === 'idle') {
                clearInterval(pollingInterval); pollingInterval = null;
                const btn = document.getElementById('checkBtn');
                btn.disabled = false; btn.innerHTML = '🚀 بدء الفحص';
                await loadLearnedBlocks();
            }
        }

        function addLog(text, className, scroll = true) {
            const box = document.getElementById('logsBox');
            const div = document.createElement('div');
            div.className = `log-line ${className}`; div.innerText = text;
            box.appendChild(div);
            if (scroll) box.scrollTop = box.scrollHeight;
        }

        function downloadTXT() { window.location.href = '/api/download-txt'; }
        function downloadVCF() { window.location.href = '/api/download-vcf'; }
        function downloadCurrent() { window.location.href = '/api/download-current'; }

        document.addEventListener('DOMContentLoaded', () => { loadInitialStats(); });
    </script>
</body>
</html>
"""

# ========== التوليد الذكي ==========
def generate_numbers_func(country, count):
    """التوليد الذكي: يفضّل البادئات الحقيقية من الأرقام الصحيحة"""
    valid_history = load_set(VALID_FILE)
    checked_history = load_set(CHECKED_FILE)
    existing = valid_history | checked_history

    config = COUNTRIES[country]
    learned_blocks = extract_learned_blocks(country, block_length=3)

    # بناء مجموعة الاختيار الموزونة
    if learned_blocks:
        learned_total = sum(learned_blocks.values())
        pool = []
        # 70% من البادئات المتعلَّمة (موزونة بالتكرار)
        for block, freq in learned_blocks.items():
            weight = (freq / learned_total) * 0.7
            pool.append((block, weight))
        # 30% استكشاف من البادئات العامة (لاكتشاف بادئات جديدة)
        for prefix in config["prefixes"]:
            weight = 0.3 / len(config["prefixes"])
            pool.append((prefix, weight))
    else:
        # لا توجد بيانات تعلم بعد — استخدم البادئات العامة
        pool = [(p, 1.0 / len(config["prefixes"])) for p in config["prefixes"]]

    blocks_list = [b for b, w in pool]
    weights_list = [w for b, w in pool]

    numbers = []
    attempts = 0
    max_attempts = count * 100

    while len(numbers) < count and attempts < max_attempts:
        block = random.choices(blocks_list, weights=weights_list, k=1)[0]
        rest_length = config["length"] - len(block)
        if rest_length <= 0:
            attempts += 1
            continue
        rest = "".join(random.choices(string.digits, k=rest_length))
        num = f"{config['code']}{block}{rest}"
        if num not in existing and num not in numbers:
            numbers.append(num)
        attempts += 1

    save_current_batch(numbers)
    append_to_file(GENERATED_FILE, numbers)
    return numbers, learned_blocks

def process_apify(numbers):
    global current_status, logs, valid_numbers, stats
    apify_token = get_apify_token()
    if not apify_token:
        logs.append("❌ لم يتم تعيين APIFY_API_TOKEN.")
        current_status = "idle"; return
    logs.append(f"[*] جاري إرسال {len(numbers)} رقم للفحص...")
    chunk_size = 20
    chunks = [numbers[i:i + chunk_size] for i in range(0, len(numbers), chunk_size)]
    for idx, chunk in enumerate(chunks):
        logs.append(f"[*] فحص الدفعة {idx+1}/{len(chunks)} (عدد: {len(chunk)})...")
        url = f"https://api.apify.com/v2/acts/apivault_labs~whatsapp-number-validator/run-sync-get-dataset-items?token={apify_token}"
        try:
            response = requests.post(url, json={"phoneNumbers": chunk}, timeout=120)
            if response.status_code in [200, 201]:
                try:
                    data = response.json()
                except json.JSONDecodeError:
                    logs.append(f"❌ الدفعة {idx+1}: رد غير JSON.")
                    continue
                if not data or (isinstance(data, dict) and "error" in data):
                    logs.append(f"❌ الدفعة {idx+1}: استجابة غير صالحة.")
                    continue
                processed = 0
                checked_chunk, valid_chunk = [], []
                for item in data:
                    if not isinstance(item, dict): continue
                    phone = item.get("input") or item.get("e164") or item.get("phone")
                    has_wa = item.get("whatsapp")
                    if "summary" in item and not phone: continue
                    if phone is None: continue
                    processed += 1
                    stats["total"] += 1
                    checked_chunk.append(phone)
                    if has_wa:
                        logs.append(f"✅ مسجل: {phone}")
                        valid_numbers.append(phone)
                        valid_chunk.append(phone)
                        stats["valid"] += 1
                    else:
                        logs.append(f"❌ غير مسجل: {phone}")
                        stats["invalid"] += 1
                if checked_chunk: append_to_file(CHECKED_FILE, checked_chunk)
                if valid_chunk: append_to_file(VALID_FILE, valid_chunk)
                if processed == 0: logs.append(f"⚠️ الدفعة {idx+1}: لم يتم التعرف على أي حقل.")
            else:
                logs.append(f"❌ الدفعة {idx+1} (كود {response.status_code}).")
        except Exception as e:
            logs.append(f"❌ خطأ في الدفعة {idx+1}: {str(e)[:150]}")
        time.sleep(2)
    logs.append(f"--- اكتملت العملية. {stats['valid']} رقم مسجل ---")
    if stats['valid'] > 0:
        logs.append(f"🧠 تم تحديث البادئات المتعلَّمة — التوليد القادم سيكون أذكى!")
    current_status = "idle"

# ========== Flask Routes ==========
@app.route('/')
def index():
    if not session.get('logged_in'): return redirect(url_for('login'))
    return render_template_string(DASHBOARD_TEMPLATE, countries=COUNTRIES, apify_token=load_settings().get("APIFY_TOKEN", ""))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] == 'As3ad' and request.form['password'] == 'As3ad':
            session['logged_in'] = True
            return redirect(url_for('index'))
        else: error = "بيانات الدخول غير صحيحة."
    return render_template_string(LOGIN_TEMPLATE, error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/api/save-settings', methods=['POST'])
def save_settings_api():
    data = request.json
    save_settings({"APIFY_TOKEN": data.get("apify_token", "")})
    return {"status": "success"}

@app.route('/api/reset-history', methods=['POST'])
def reset_history():
    global generated_numbers
    for f in [CHECKED_FILE, VALID_FILE, GENERATED_FILE, MESSAGED_FILE, CURRENT_BATCH_FILE]:
        if os.path.exists(f): os.remove(f)
    generated_numbers = []
    return {"status": "success"}

@app.route('/api/generate', methods=['POST'])
def generate_api():
    global generated_numbers, logs, stats
    data = request.json
    country = data.get('country'); count = int(data.get('count', 10))
    nums, learned = generate_numbers_func(country, count)
    generated_numbers = nums
    logs.clear(); stats = {"total": 0, "valid": 0, "invalid": 0}
    logs.append(f"[*] تم توليد {len(nums)} رقم لدولة {COUNTRIES[country]['ar']}.")
    total = len(load_set(GENERATED_FILE))
    return {
        "count": len(nums),
        "preview": nums[:5],
        "total": total,
        "learned_blocks_count": len(learned),
        "learned_ratio": 0.7 if learned else 0.0
    }

@app.route('/api/check', methods=['POST'])
def check_api():
    global current_status, logs, stats, valid_numbers
    data = request.json
    specific = data.get('specific', '').strip()
    if current_status == "running": return {"error": "قيد التشغيل"}, 400
    logs.clear(); stats = {"total": 0, "valid": 0, "invalid": 0}; current_status = "running"
    valid_numbers.clear()
    if specific:
        numbers = [specific]; logs.append(f"[>] فحص رقم محدد: {specific}")
    else:
        numbers = generated_numbers; logs.append(f"[>] فحص {len(numbers)} رقم...")
    threading.Thread(target=process_apify, args=(numbers,)).start()
    return {"status": "started"}

@app.route('/api/status')
def status_api():
    return {"status": current_status, "logs": logs, "stats": stats, "total_generated": len(load_set(GENERATED_FILE))}

@app.route('/api/current-batch')
def current_batch():
    return {"numbers": generated_numbers}

@app.route('/api/learned-blocks')
def learned_blocks_api():
    return get_learning_summary()

@app.route('/api/download-current')
def download_current():
    numbers = generated_numbers if generated_numbers else load_list(CURRENT_BATCH_FILE)
    if not numbers: return "لا توجد أرقام مولدة حالياً.", 404
    return Response("\n".join(numbers), mimetype="text/plain", headers={"Content-Disposition": "attachment;filename=current_batch.txt"})

@app.route('/api/download-txt')
def download_txt():
    valid_all = load_set(VALID_FILE)
    if not valid_all: return "لا توجد أرقام ناجحة.", 404
    return Response("\n".join(valid_all), mimetype="text/plain", headers={"Content-Disposition": "attachment;filename=all_valid_numbers.txt"})

@app.route('/api/download-vcf')
def download_vcf():
    valid_all = load_set(VALID_FILE)
    if not valid_all: return "لا توجد أرقام ناجحة.", 404
    return Response(generate_vcf(valid_all), mimetype="text/vcard", headers={"Content-Disposition": "attachment;filename=whatsapp_contacts.vcf"})

generated_numbers = load_list(CURRENT_BATCH_FILE)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
