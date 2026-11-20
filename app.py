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

current_status = "idle"
logs = []
generated_numbers = []
valid_numbers = []
stats = {"total": 0, "valid": 0, "invalid": 0}

send_status = "idle"
send_logs = []
send_progress = {"current": 0, "total": 0, "success": 0, "failed": 0}

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

def get_wasender_key():
    return load_settings().get("WASENDER_API_KEY") or os.environ.get("WASENDER_API_KEY", "")

def load_set(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def append_to_file(filename, items):
    with open(filename, "a", encoding="utf-8") as f:
        for item in items:
            f.write(item + "\n")

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

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>As3ad Platform | System Access</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap" rel="stylesheet">
    <style>
        :root { --bg: #050810; --panel: rgba(15, 23, 42, 0.8); --primary: #00f0ff; --primary-hover: #00c4d1; --text: #e2e8f0; --muted: #64748b; --danger: #f43f5e; --border: rgba(0, 240, 255, 0.2); }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Cairo', sans-serif; }
        body { background-color: var(--bg); color: var(--text); display: flex; justify-content: center; align-items: center; height: 100vh; overflow: hidden; background-image: radial-gradient(circle at 10% 20%, rgba(0, 240, 255, 0.15) 0%, transparent 40%), radial-gradient(circle at 90% 80%, rgba(16, 185, 129, 0.1) 0%, transparent 40%); }
        .login-box { background: var(--panel); backdrop-filter: blur(20px); padding: 50px 40px; border-radius: 24px; box-shadow: 0 30px 60px rgba(0,0,0,0.6), inset 0 0 0 1px var(--border); width: 100%; max-width: 420px; text-align: center; animation: fadeIn 0.8s ease-out; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        .logo-icon { font-size: 48px; margin-bottom: 15px; display: inline-block; filter: drop-shadow(0 0 10px var(--primary)); }
        h2 { color: var(--text); margin-bottom: 10px; font-weight: 900; font-size: 28px; letter-spacing: -0.5px; }
        p.subtitle { color: var(--muted); margin-bottom: 35px; font-size: 15px; font-weight: 600; }
        .input-group { margin-bottom: 20px; text-align: right; position: relative; }
        label { display: block; margin-bottom: 8px; font-size: 14px; color: #94a3b8; font-weight: 700; }
        input { width: 100%; padding: 16px; background: rgba(0,0,0,0.3); border: 1px solid #334155; border-radius: 12px; color: white; outline: none; transition: all 0.3s; font-family: 'Cairo'; font-size: 15px; }
        input:focus { border-color: var(--primary); box-shadow: 0 0 15px rgba(0, 240, 255, 0.2); }
        button { width: 100%; padding: 16px; background: var(--primary); color: #000; border: none; border-radius: 12px; font-size: 16px; font-weight: 900; cursor: pointer; transition: all 0.3s; margin-top: 10px; font-family: 'Cairo'; text-transform: uppercase; letter-spacing: 1px; }
        button:hover { background: var(--primary-hover); box-shadow: 0 0 20px rgba(0, 240, 255, 0.4); transform: translateY(-2px); }
        .error { color: var(--danger); background: rgba(244, 63, 94, 0.1); padding: 12px; border-radius: 8px; margin-bottom: 20px; font-size: 14px; font-weight: 700; border: 1px solid rgba(244, 63, 94, 0.3); }
    </style>
</head>
<body>
    <div class="login-box">
        <div class="logo-icon">⚡</div>
        <h2>As3ad Platform</h2>
        <p class="subtitle">منصة الخدمات الذكية المتكاملة</p>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="POST">
            <div class="input-group"><label>اسم المستخدم</label><input type="text" name="username" placeholder="أدخل اسم المستخدم" required autocomplete="off"></div>
            <div class="input-group"><label>كلمة المرور</label><input type="password" name="password" placeholder="••••••" required></div>
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
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>As3ad Platform | Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap" rel="stylesheet">
    <style>
        :root { --bg: #050810; --panel: #0f172a; --panel-light: #1e293b; --primary: #00f0ff; --success: #10b981; --danger: #f43f5e; --warning: #f59e0b; --text: #e2e8f0; --muted: #64748b; --border: #1e293b; }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Cairo', sans-serif; }
        body { background-color: var(--bg); color: var(--text); display: flex; height: 100vh; overflow: hidden; }
        .sidebar { width: 280px; background: var(--panel); border-left: 1px solid var(--border); display: flex; flex-direction: column; box-shadow: 10px 0 30px rgba(0,0,0,0.3); z-index: 10; }
        .brand { padding: 30px 20px; font-size: 24px; font-weight: 900; display: flex; align-items: center; gap: 10px; border-bottom: 1px solid var(--border); color: var(--text); }
        .brand-icon { color: var(--primary); font-size: 28px; filter: drop-shadow(0 0 8px var(--primary)); }
        .nav-menu { padding: 20px 15px; flex: 1; display: flex; flex-direction: column; gap: 10px; }
        .nav-item { padding: 16px 20px; border-radius: 12px; cursor: pointer; display: flex; align-items: center; gap: 15px; font-weight: 700; color: var(--muted); transition: all 0.3s; border: 1px solid transparent; }
        .nav-item:hover { background: rgba(0, 240, 255, 0.05); color: var(--text); }
        .nav-item.active { background: rgba(0, 240, 255, 0.1); color: var(--primary); border: 1px solid rgba(0, 240, 255, 0.2); box-shadow: 0 0 15px rgba(0,240,255,0.1); }
        .logout-btn { padding: 20px; border-top: 1px solid var(--border); color: var(--danger); text-decoration: none; font-weight: 900; display: flex; justify-content: center; transition: 0.3s; }
        .logout-btn:hover { background: rgba(244, 63, 94, 0.1); color: #ff6b6b; }
        .main-content { flex: 1; overflow-y: auto; padding: 40px; display: none; }
        .main-content.active { display: block; animation: slideUp 0.5s ease-out; }
        @keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        .header-title { font-size: 28px; font-weight: 900; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: center; color: var(--text); }
        .stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 25px; margin-bottom: 40px; }
        .stat-card { background: var(--panel-light); border: 1px solid var(--border); border-radius: 16px; padding: 25px; display: flex; align-items: center; gap: 20px; transition: transform 0.3s; }
        .stat-card:hover { transform: translateY(-5px); }
        .stat-icon { width: 65px; height: 65px; border-radius: 16px; display: flex; justify-content: center; align-items: center; font-size: 28px; }
        .stat-icon.total { background: rgba(0, 240, 255, 0.1); color: var(--primary); border: 1px solid rgba(0,240,255,0.2); }
        .stat-icon.valid { background: rgba(16, 185, 129, 0.1); color: var(--success); border: 1px solid rgba(16,185,129,0.2); }
        .stat-icon.invalid { background: rgba(244, 63, 94, 0.1); color: var(--danger); border: 1px solid rgba(244,63,94,0.2); }
        .stat-info h4 { color: var(--muted); font-size: 14px; margin-bottom: 8px; font-weight: 700; }
        .stat-info span { font-size: 32px; font-weight: 900; color: var(--text); }
        .content-grid { display: grid; grid-template-columns: 380px 1fr; gap: 30px; }
        .panel { background: var(--panel); border: 1px solid var(--border); border-radius: 20px; padding: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
        .panel-title { font-size: 20px; font-weight: 900; margin-bottom: 25px; padding-bottom: 15px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 10px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 10px; font-size: 14px; color: var(--muted); font-weight: 700; }
        select, input, textarea { width: 100%; padding: 14px; background: rgba(0,0,0,0.3); border: 1px solid #334155; border-radius: 12px; color: white; outline: none; font-family: 'Cairo'; font-size: 15px; transition: 0.3s; }
        select:focus, input:focus, textarea:focus { border-color: var(--primary); box-shadow: 0 0 10px rgba(0,240,255,0.1); }
        textarea { resize: vertical; min-height: 120px; }
        .btn { width: 100%; padding: 16px; border: none; border-radius: 12px; font-weight: 900; cursor: pointer; font-family: 'Cairo'; font-size: 16px; display: flex; justify-content: center; align-items: center; gap: 10px; margin-top: 10px; transition: 0.3s; }
        .btn-primary { background: var(--primary); color: #000; }
        .btn-primary:hover { box-shadow: 0 0 20px rgba(0, 240, 255, 0.4); transform: translateY(-2px); }
        .btn-success { background: var(--success); color: white; }
        .btn-success:hover { box-shadow: 0 0 20px rgba(16, 185, 129, 0.4); transform: translateY(-2px); }
        .btn-warning { background: var(--warning); color: #000; }
        .btn-warning:hover { box-shadow: 0 0 20px rgba(245, 158, 11, 0.4); transform: translateY(-2px); }
        .btn-danger { background: rgba(244, 63, 94, 0.1); color: var(--danger); border: 1px solid var(--danger); }
        .btn-danger:hover { background: var(--danger); color: white; }
        .btn:disabled { background: #1e293b; color: var(--muted); cursor: not-allowed; transform: none; box-shadow: none; }
        .terminal-panel { background: #000000; border: 1px solid var(--border); border-radius: 20px; display: flex; flex-direction: column; height: 600px; overflow: hidden; box-shadow: inset 0 0 30px rgba(0,0,0,0.8); }
        .terminal-header { background: var(--panel-light); padding: 15px 20px; display: flex; align-items: center; gap: 8px; border-bottom: 1px solid var(--border); }
        .dot { width: 12px; height: 12px; border-radius: 50%; }
        .dot.red { background: #ef4444; } .dot.yellow { background: #f59e0b; } .dot.green { background: #10b981; }
        .terminal-title { margin-right: auto; font-size: 13px; color: var(--muted); font-family: monospace; font-weight: bold; }
        .terminal-body { padding: 20px; flex: 1; overflow-y: auto; font-family: 'Consolas', monospace; font-size: 14px; line-height: 1.6; direction: ltr; text-align: left; }
        .log-line { margin-bottom: 6px; padding: 4px 8px; border-radius: 4px; }
        .log-info { color: var(--primary); background: rgba(0, 240, 255, 0.05); }
        .log-success { color: var(--success); background: rgba(16, 185, 129, 0.05); border-left: 3px solid var(--success); }
        .log-error { color: var(--danger); background: rgba(244, 63, 94, 0.05); border-left: 3px solid var(--danger); }
        .log-warn { color: #f59e0b; background: rgba(245, 158, 11, 0.05); border-left: 3px solid #f59e0b; }
        .export-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .export-card { background: var(--panel); border: 1px solid var(--border); border-radius: 16px; padding: 25px; display: flex; flex-direction: column; justify-content: space-between; }
        .export-card h4 { font-size: 18px; margin-bottom: 10px; color: var(--primary); }
        .export-card p { color: var(--muted); font-size: 13px; margin-bottom: 15px; line-height: 1.6; }
        @media (max-width: 1024px) { .content-grid { grid-template-columns: 1fr; } .stats-grid { grid-template-columns: 1fr; } .export-grid { grid-template-columns: 1fr; } }
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
            <button onclick="resetHistory()" class="btn btn-danger" style="width: auto; padding: 10px 20px; margin: 0; font-size: 14px;">🗑️ مسح سجل الأرقام</button>
        </div>
        <div class="stats-grid">
            <div class="stat-card"><div class="stat-icon total">📊</div><div class="stat-info"><h4>الأرقام المفحوصة</h4><span id="statTotal">0</span></div></div>
            <div class="stat-card"><div class="stat-icon valid">✅</div><div class="stat-info"><h4>مسجلة (واتساب)</h4><span id="statValid">0</span></div></div>
            <div class="stat-card"><div class="stat-icon invalid">❌</div><div class="stat-info"><h4>غير مسجلة</h4><span id="statInvalid">0</span></div></div>
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
                <button class="btn btn-primary" onclick="generateNumbers()" id="genBtn">✨ توليد الأرقام</button>
                <hr style="border-color: var(--border); margin: 25px 0;">
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
    </div>

    <div class="main-content" id="export-section">
        <div class="header-title">تصدير جهات الاتصال</div>
        <div class="export-grid">
            <div class="export-card">
                <div>
                    <h4>📇 استيراد كجهات اتصال (VCF)</h4>
                    <p>قم بتحميل الأرقام كملف VCF (vCard) لاستيرادها مباشرة إلى جهات اتصال هاتفك. سيتم تسمية كل جهة اتصال برقم تصاعدي (WA-1, WA-2, ...).</p>
                </div>
                <button onclick="downloadVCF()" class="btn btn-primary">⬇️ تحميل ملف VCF</button>
            </div>
            <div class="export-card">
                <div>
                    <h4>📄 تحميل كملف نصي (TXT)</h4>
                    <p>قم بتحميل الأرقام كملف نصي بسيط يحتوي على الأرقام فقط بصيغة دولية. مناسب للنسخ واللصق أو للاستخدام في برامج أخرى.</p>
                </div>
                <button onclick="downloadTXT()" class="btn btn-warning">⬇️ تحميل ملف TXT</button>
            </div>
        </div>
    </div>

    <div class="main-content" id="settings-section">
        <div class="header-title">إعدادات المنصة</div>
        <div class="panel" style="max-width: 600px; margin: 0 auto;">
            <div class="panel-title">🔑 مفاتيح API</div>
            <p style="font-size: 14px; color: var(--muted); margin-bottom: 25px; line-height: 1.6;">
                يمكنك تغيير المفاتيح هنا مباشرة. <br>
                <strong style="color: var(--danger);">ملاحظة:</strong> التغيير هنا ساري المفعول حتى يتم إعادة تشغيل السيرفر.
            </p>
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
        async function saveSettings() {
            const apifyToken = document.getElementById('apifyTokenInput').value;
            const btn = document.getElementById('saveBtn');
            btn.disabled = true; btn.innerHTML = `⏳ جاري الحفظ...`;
            const res = await fetch('/api/save-settings', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ apify_token: apifyToken }) });
            if (res.ok) alert("تم حفظ الإعدادات بنجاح."); else alert("حدث خطأ أثناء الحفظ.");
            btn.disabled = false; btn.innerHTML = `💾 حفظ المفاتيح`;
        }
        async function resetHistory() {
            if (!confirm("هل أنت متأكد من مسح سجل الأرقام؟")) return;
            const res = await fetch('/api/reset-history', { method: 'POST' });
            if (res.ok) { alert("تم مسح السجل بنجاح."); location.reload(); }
        }
        async function generateNumbers() {
            const country = document.getElementById('country').value;
            const count = document.getElementById('count').value;
            const btn = document.getElementById('genBtn');
            btn.disabled = true; btn.innerHTML = `⏳ جاري التوليد...`;
            const res = await fetch('/api/generate', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({country, count}) });
            const data = await res.json();
            document.getElementById('checkBtn').disabled = false;
            btn.disabled = false; btn.innerHTML = `✨ توليد الأرقام`;
            addLog(`[+] تم توليد ${data.count} رقم جديد.`, 'log-success');
        }
        async function startChecking() {
            const specific = document.getElementById('specific').value;
            const btn = document.getElementById('checkBtn');
            btn.disabled = true; btn.innerHTML = `⏳ جاري الفحص...`;
            document.getElementById('logsBox').innerHTML = "";
            document.getElementById('statTotal').innerText = "0";
            document.getElementById('statValid').innerText = "0";
            document.getElementById('statInvalid').innerText = "0";
            const res = await fetch('/api/check', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({specific}) });
            if (res.ok && !pollingInterval) { pollingInterval = setInterval(pollStatus, 1500); }
        }
        async function pollStatus() {
            const res = await fetch('/api/status');
            const data = await res.json();
            if (data.stats) {
                document.getElementById('statTotal').innerText = data.stats.total;
                document.getElementById('statValid').innerText = data.stats.valid;
                document.getElementById('statInvalid').innerText = data.stats.invalid;
            }
            if (data.logs.length > 0) {
                const box = document.getElementById('logsBox'); box.innerHTML = "";
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
                btn.disabled = false; btn.innerHTML = `🚀 بدء الفحص`;
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
    </script>
</body>
</html>
"""

def generate_numbers_func(country, count):
    checked_history = load_set(CHECKED_FILE)
    generated_history = load_set(GENERATED_FILE)
    existing = checked_history | generated_history
    config = COUNTRIES[country]
    numbers = []
    attempts = 0
    max_attempts = count * 50
    while len(numbers) < count and attempts < max_attempts:
        prefix = random.choice(config["prefixes"])
        rest_length = config["length"] - len(prefix)
        rest = "".join(random.choices(string.digits, k=rest_length))
        num = f"{config['code']}{prefix}{rest}"
        if num not in existing and num not in numbers:
            numbers.append(num)
        attempts += 1
    if numbers:
        append_to_file(GENERATED_FILE, numbers)
    return numbers

def process_apify(numbers):
    global current_status, logs, valid_numbers, stats
    apify_token = get_apify_token()
    if not apify_token:
        logs.append("❌ خطأ: لم يتم تعيين APIFY_API_TOKEN.")
        current_status = "idle"; return
    logs.append(f"[*] جاري إرسال {len(numbers)} رقم إلى محرك الفحص...")
    chunk_size = 20
    chunks = [numbers[i:i + chunk_size] for i in range(0, len(numbers), chunk_size)]
    for idx, chunk in enumerate(chunks):
        logs.append(f"[*] جاري فحص الدفعة {idx+1} من {len(chunks)} (عدد: {len(chunk)})...")
        url = f"https://api.apify.com/v2/acts/apivault_labs~whatsapp-number-validator/run-sync-get-dataset-items?token={apify_token}"
        payload = {"phoneNumbers": chunk}
        try:
            response = requests.post(url, json=payload, timeout=120)
            raw_preview = response.text[:500] if response.text else "(empty)"
            if response.status_code in [200, 201]:
                try:
                    data = response.json()
                except json.JSONDecodeError:
                    logs.append(f"❌ الدفعة {idx+1}: الرد ليس JSON.")
                    continue
                if not data or (isinstance(data, dict) and "error" in data):
                    logs.append(f"❌ الدفعة {idx+1}: استجابة غير صالحة: {raw_preview}")
                    continue
                processed = 0
                current_chunk_checked = []
                current_chunk_valid = []
                for item in data:
                    if not isinstance(item, dict): continue
                    phone = item.get("input") or item.get("e164") or item.get("phone")
                    has_wa = item.get("whatsapp")
                    if "summary" in item and not phone: continue
                    if phone is None: continue
                    processed += 1
                    stats["total"] += 1
                    current_chunk_checked.append(phone)
                    if has_wa:
                        logs.append(f"✅ مسجل: {phone}")
                        valid_numbers.append(phone)
                        current_chunk_valid.append(phone)
                        stats["valid"] += 1
                    else:
                        logs.append(f"❌ غير مسجل: {phone}")
                        stats["invalid"] += 1
                if current_chunk_checked: append_to_file(CHECKED_FILE, current_chunk_checked)
                if current_chunk_valid: append_to_file(VALID_FILE, current_chunk_valid)
                if processed == 0:
                    logs.append(f"⚠️ الدفعة {idx+1}: لم يتم التعرف على أي حقل.")
            else:
                logs.append(f"❌ الدفعة {idx+1} (كود {response.status_code}): {raw_preview}")
        except Exception as e:
            logs.append(f"❌ خطأ في الدفعة {idx+1}: {str(e)[:150]}")
        time.sleep(2)
    logs.append(f"--- اكتملت العملية. تم العثور على {stats['valid']} رقم مسجل ---")
    current_status = "idle"

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
    for f in [CHECKED_FILE, VALID_FILE, GENERATED_FILE, MESSAGED_FILE]:
        if os.path.exists(f): os.remove(f)
    return {"status": "success"}

@app.route('/api/generate', methods=['POST'])
def generate_api():
    global generated_numbers, logs, stats
    data = request.json
    country = data.get('country'); count = int(data.get('count', 10))
    generated_numbers = generate_numbers_func(country, count)
    logs.clear(); stats = {"total": 0, "valid": 0, "invalid": 0}
    logs.append(f"[*] تم توليد {len(generated_numbers)} رقم جديد لدولة {COUNTRIES[country]['ar']} (تم تخطي الأرقام المولدة والمفحوصة سابقاً).")
    return {"count": len(generated_numbers)}

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
    return {"status": current_status, "logs": logs, "stats": stats}

@app.route('/api/download-txt')
def download_txt():
    valid_all = load_set(VALID_FILE)
    if not valid_all: return "لا توجد أرقام ناجحة.", 404
    output = "\n".join(valid_all)
    return Response(output, mimetype="text/plain", headers={"Content-Disposition": "attachment;filename=all_valid_numbers.txt"})

@app.route('/api/download-vcf')
def download_vcf():
    valid_all = load_set(VALID_FILE)
    if not valid_all: return "لا توجد أرقام ناجحة.", 404
    vcf_content = generate_vcf(valid_all)
    return Response(vcf_content, mimetype="text/vcard", headers={"Content-Disposition": "attachment;filename=whatsapp_contacts.vcf"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
