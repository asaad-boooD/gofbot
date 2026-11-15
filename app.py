import os
import random
import string
import threading
import requests
import io
import time
from flask import Flask, request, render_template_string, session, redirect, url_for, Response, jsonify

app = Flask(__name__)
app.secret_key = "As3ad_Enterprise_Secret_2024"

APIFY_TOKEN = os.environ.get("APIFY_API_TOKEN", "")
WASERVIX_KEY = os.environ.get("WASERVIX_API_KEY", "")
WASERVIX_URL = "https://api.waservix.com/v1/messages"

# --- حالة منصة الواتساب ---
current_status = "idle"
logs = []
generated_numbers = []
valid_numbers = []
stats = {"total": 0, "valid": 0, "invalid": 0}

# --- حالة مرسل الرسائل ---
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

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>As3ad Platform | تسجيل الدخول</title>
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap" rel="stylesheet">
    <style>
        :root { --bg: #0b1120; --surface: #1e293b; --primary: #6366f1; --primary-hover: #4f46e5; --text: #f8fafc; --danger: #f43f5e; --border: #334155; }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Tajawal', sans-serif; }
        body { background-color: var(--bg); color: var(--text); display: flex; justify-content: center; align-items: center; height: 100vh; background-image: radial-gradient(circle at 15% 50%, rgba(99, 102, 241, 0.15), transparent 25%), radial-gradient(circle at 85% 30%, rgba(244, 63, 94, 0.15), transparent 25%); }
        .login-box { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(10px); padding: 50px 40px; border-radius: 24px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); width: 100%; max-width: 420px; border: 1px solid rgba(255,255,255,0.05); text-align: center; }
        .logo-icon { font-size: 40px; margin-bottom: 15px; display: inline-block; }
        h2 { color: var(--text); margin-bottom: 10px; font-weight: 700; font-size: 28px; letter-spacing: -0.5px; }
        p.subtitle { color: #94a3b8; margin-bottom: 35px; font-size: 15px; }
        .input-group { margin-bottom: 20px; text-align: right; }
        label { display: block; margin-bottom: 8px; font-size: 14px; color: #cbd5e1; font-weight: 500; }
        input { width: 100%; padding: 14px 16px; background: #0f172a; border: 1px solid var(--border); border-radius: 12px; color: white; outline: none; transition: all 0.3s; font-family: 'Tajawal'; font-size: 15px; }
        input:focus { border-color: var(--primary); box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2); }
        button { width: 100%; padding: 16px; background: var(--primary); color: white; border: none; border-radius: 12px; font-size: 16px; font-weight: 700; cursor: pointer; transition: all 0.3s; margin-top: 10px; font-family: 'Tajawal'; }
        button:hover { background: var(--primary-hover); transform: translateY(-2px); box-shadow: 0 10px 20px -10px var(--primary); }
        .error { color: var(--danger); background: rgba(244, 63, 94, 0.1); padding: 12px; border-radius: 8px; margin-bottom: 20px; font-size: 14px; border: 1px solid rgba(244, 63, 94, 0.2); }
    </style>
</head>
<body>
    <div class="login-box">
        <div class="logo-icon">🚀</div>
        <h2>As3ad Platform</h2>
        <p class="subtitle">منصة الخدمات الذكية المتكاملة</p>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="POST">
            <div class="input-group">
                <label>اسم المستخدم</label>
                <input type="text" name="username" placeholder="أدخل اسم المستخدم" required autocomplete="off">
            </div>
            <div class="input-group">
                <label>كلمة المرور</label>
                <input type="password" name="password" placeholder="أدخل كلمة المرور" required>
            </div>
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
    <title>As3ad Platform | لوحة التحكم</title>
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap" rel="stylesheet">
    <style>
        :root { --bg: #0b1120; --surface: #1e293b; --primary: #6366f1; --success: #10b981; --danger: #f43f5e; --text: #f8fafc; --muted: #94a3b8; --border: #334155; --sidebar: #0f172a; }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Tajawal', sans-serif; }
        body { background-color: var(--bg); color: var(--text); display: flex; height: 100vh; overflow: hidden; }
        
        .sidebar { width: 260px; background: var(--sidebar); border-left: 1px solid var(--border); display: flex; flex-direction: column; }
        .brand { padding: 25px 20px; font-size: 22px; font-weight: 800; color: var(--text); display: flex; align-items: center; gap: 10px; border-bottom: 1px solid var(--border); }
        .brand-icon { color: var(--primary); font-size: 26px; }
        .nav-menu { padding: 20px 10px; flex: 1; display: flex; flex-direction: column; gap: 10px; }
        .nav-item { padding: 15px 20px; border-radius: 12px; cursor: pointer; display: flex; align-items: center; gap: 15px; font-weight: 600; color: var(--muted); transition: 0.3s; }
        .nav-item:hover { background: rgba(255,255,255,0.05); color: var(--text); }
        .nav-item.active { background: rgba(99, 102, 241, 0.1); color: var(--primary); border-right: 4px solid var(--primary); }
        .logout-btn { padding: 20px; border-top: 1px solid var(--border); color: var(--danger); text-decoration: none; font-weight: 700; display: flex; justify-content: center; transition: 0.3s; }
        .logout-btn:hover { background: rgba(244, 63, 94, 0.1); }

        .main-content { flex: 1; overflow-y: auto; padding: 30px; display: none; }
        .main-content.active { display: block; }

        .header-title { font-size: 24px; font-weight: 800; margin-bottom: 25px; color: var(--text); display: flex; align-items: center; gap: 10px; }
        .stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 25px; display: flex; align-items: center; gap: 20px; }
        .stat-icon { width: 60px; height: 60px; border-radius: 12px; display: flex; justify-content: center; align-items: center; font-size: 24px; }
        .stat-icon.total { background: rgba(99, 102, 241, 0.1); color: var(--primary); }
        .stat-icon.valid { background: rgba(16, 185, 129, 0.1); color: var(--success); }
        .stat-icon.invalid { background: rgba(244, 63, 94, 0.1); color: var(--danger); }
        .stat-info h4 { color: var(--muted); font-size: 14px; margin-bottom: 5px; }
        .stat-info span { font-size: 28px; font-weight: 800; color: var(--text); }

        .content-grid { display: grid; grid-template-columns: 400px 1fr; gap: 30px; }
        .panel { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 30px; }
        .panel-title { font-size: 18px; font-weight: 700; margin-bottom: 25px; padding-bottom: 15px; border-bottom: 1px solid var(--border); }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; font-size: 14px; color: #cbd5e1; font-weight: 500; }
        select, input, textarea { width: 100%; padding: 14px; background: var(--bg); border: 1px solid var(--border); border-radius: 10px; color: white; outline: none; font-family: 'Tajawal'; font-size: 15px; }
        textarea { resize: vertical; min-height: 120px; }
        .btn { width: 100%; padding: 16px; border: none; border-radius: 10px; font-weight: 700; cursor: pointer; font-family: 'Tajawal'; font-size: 16px; display: flex; justify-content: center; align-items: center; gap: 10px; margin-top: 10px; transition: 0.3s; }
        .btn-primary { background: var(--primary); color: white; }
        .btn-primary:hover { background: #4f46e5; }
        .btn-success { background: var(--success); color: white; }
        .btn-success:hover { background: #059669; }
        .btn:disabled { background: #334155; color: var(--muted); cursor: not-allowed; }

        .terminal-panel { background: #020617; border: 1px solid var(--border); border-radius: 16px; display: flex; flex-direction: column; height: 550px; }
        .terminal-header { background: #0f172a; padding: 15px 20px; display: flex; align-items: center; gap: 8px; border-bottom: 1px solid var(--border); }
        .dot { width: 12px; height: 12px; border-radius: 50%; }
        .dot.red { background: #ef4444; } .dot.yellow { background: #f59e0b; } .dot.green { background: #10b981; }
        .terminal-title { margin-right: auto; font-size: 13px; color: var(--muted); font-family: monospace; }
        .terminal-body { padding: 20px; flex: 1; overflow-y: auto; font-family: monospace; font-size: 14px; line-height: 1.6; direction: ltr; text-align: left; }
        .log-line { margin-bottom: 6px; padding: 4px 8px; border-radius: 4px; }
        .log-info { color: #38bdf8; background: rgba(56, 189, 248, 0.1); }
        .log-success { color: var(--success); background: rgba(16, 185, 129, 0.1); border-left: 3px solid var(--success); }
        .log-error { color: var(--danger); background: rgba(244, 63, 94, 0.1); border-left: 3px solid var(--danger); }

        .progress-container { width: 100%; background: var(--bg); border-radius: 10px; margin: 20px 0; border: 1px solid var(--border); height: 20px; overflow: hidden; }
        .progress-bar { height: 100%; background: var(--primary); width: 0%; transition: width 0.3s; }

        @media (max-width: 1024px) { .content-grid { grid-template-columns: 1fr; } .stats-grid { grid-template-columns: 1fr; } }
        @media (max-width: 768px) {
            body { flex-direction: column; }
            .sidebar { width: 100%; border-left: none; border-bottom: 1px solid var(--border); flex-direction: row; align-items: center; padding: 0 10px; height: 60px; }
            .brand { padding: 10px; font-size: 18px; border-bottom: none; }
            .nav-menu { flex-direction: row; padding: 0; gap: 5px; }
            .nav-item { padding: 10px; font-size: 14px; }
            .logout-btn { padding: 10px; border-top: none; font-size: 14px; }
        }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="brand"><span class="brand-icon">🚀</span> As3ad</div>
        <div class="nav-menu">
            <div class="nav-item active" id="nav-wa" onclick="switchTab('wa')">📱 فاحص واتساب</div>
            <div class="nav-item" id="nav-send" onclick="switchTab('send')">📨 مرسل الرسائل</div>
        </div>
        <a href="/logout" class="logout-btn">تسجيل خروج</a>
    </div>

    <!-- WhatsApp Section -->
    <div class="main-content active" id="wa-section">
        <div class="header-title">منصة فحص أرقام الواتساب</div>
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
        <div class="download-bar" style="background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 20px; margin-top: 30px; display: flex; justify-content: space-between; align-items: center;">
            <div><h3 style="font-size: 16px; margin-bottom: 5px;">تصدير النتائج</h3><p style="color: var(--muted); font-size: 14px;">قم بتحميل ملف يحتوي على الأرقام الصالحة فقط.</p></div>
            <button onclick="downloadResults()" class="download-btn" style="padding: 12px 25px; background: linear-gradient(135deg, var(--primary), #8b5cf6); border-radius: 8px; color: white; text-decoration: none; font-weight: 700; display: flex; align-items: center; gap: 10px; transition: 0.3s; border: none; cursor: pointer; font-family: 'Tajawal'; font-size: 15px;">⬇️ تحميل الأرقام الناجحة (.txt)</button>
        </div>
    </div>

    <!-- Bulk Sender Section -->
    <div class="main-content" id="send-section">
        <div class="header-title">مرسل الرسائل الجماعية</div>
        <div class="content-grid">
            <div class="panel">
                <div class="panel-title">📝 كتابة الرسالة</div>
                <p style="font-size: 14px; color: var(--muted); margin-bottom: 15px;">الأرقام الجاهزة للإرسال: <strong id="validNumbersCount" style="color: white; font-size: 18px;">0</strong></p>
                <div class="form-group">
                    <label>نص الرسالة</label>
                    <textarea id="messageText" placeholder="اكتب رسالتك هنا..."></textarea>
                </div>
                <button class="btn btn-primary" onclick="startSending()" id="sendBtn">🚀 بدء الإرسال</button>
                
                <div class="progress-container">
                    <div class="progress-bar" id="sendProgress" style="background: var(--success);"></div>
                </div>
                <p style="text-align: center; font-size: 14px;" id="sendStats">0 / 0</p>
            </div>
            <div class="terminal-panel">
                <div class="terminal-header"><div class="dot red"></div><div class="dot yellow"></div><div class="dot green"></div><span class="terminal-title">as3ad@sender: ~/logs</span></div>
                <div class="terminal-body" id="sendLogsBox"><div class="log-line log-info">> Ready to send messages...</div></div>
            </div>
        </div>
    </div>

    <script>
        let pollingInterval = null;
        let sendPolling = null;

        function switchTab(tab) {
            document.querySelectorAll('.main-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
            
            if(tab === 'wa') {
                document.getElementById('wa-section').classList.add('active');
                document.getElementById('nav-wa').classList.add('active');
            } else if(tab === 'send') {
                document.getElementById('send-section').classList.add('active');
                document.getElementById('nav-send').classList.add('active');
                checkValidNumbers();
            }
        }

        // --- منطق الواتساب ---
        async function generateNumbers() {
            const country = document.getElementById('country').value;
            const count = document.getElementById('count').value;
            const btn = document.getElementById('genBtn');
            btn.disabled = true; btn.innerHTML = `⏳ جاري التوليد...`;
            const res = await fetch('/api/generate', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({country, count}) });
            const data = await res.json();
            document.getElementById('checkBtn').disabled = false;
            btn.disabled = false; btn.innerHTML = `✨ توليد الأرقام`;
            addLog(`[+] تم توليد ${data.count} رقم بنجاح.`, 'log-success');
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
        function downloadResults() { window.location.href = '/api/download'; }

        // --- منطق مرسل الرسائل ---
        async function checkValidNumbers() {
            const res = await fetch('/api/valid-count');
            const data = await res.json();
            document.getElementById('validNumbersCount').innerText = data.count;
        }

        async function startSending() {
            const msg = document.getElementById('messageText').value;
            if (!msg) { alert("يرجى كتابة رسالة أولاً."); return; }
            
            const btn = document.getElementById('sendBtn');
            btn.disabled = true; btn.innerHTML = `⏳ جاري الإرسال...`;
            document.getElementById('sendLogsBox').innerHTML = "";
            
            const res = await fetch('/api/send-bulk', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({message: msg}) });
            if (res.ok && !sendPolling) { sendPolling = setInterval(pollSendStatus, 2000); }
            else { alert("حدث خطأ. تأكد من وجود أرقام صالحة."); btn.disabled = false; btn.innerHTML = `🚀 بدء الإرسال`; }
        }

        async function pollSendStatus() {
            const res = await fetch('/api/send-status');
            const data = await res.json();
            
            const percent = data.progress.total > 0 ? (data.progress.current / data.progress.total) * 100 : 0;
            document.getElementById('sendProgress').style.width = percent + '%';
            document.getElementById('sendStats').innerText = `${data.progress.current} / ${data.progress.total} (نجح: ${data.progress.success} | فشل: ${data.progress.failed})`;

            if (data.logs.length > 0) {
                const box = document.getElementById('sendLogsBox'); box.innerHTML = "";
                data.logs.forEach(log => {
                    let cls = 'log-info';
                    if (log.includes('✅')) cls = 'log-success';
                    if (log.includes('❌')) cls = 'log-error';
                    addLogSend(log, cls, false);
                });
                box.scrollTop = box.scrollHeight;
            }

            if (data.status === 'idle') {
                clearInterval(sendPolling); sendPolling = null;
                const btn = document.getElementById('sendBtn');
                btn.disabled = false; btn.innerHTML = `🚀 بدء الإرسال`;
            }
        }

        function addLogSend(text, className, scroll = true) {
            const box = document.getElementById('sendLogsBox');
            const div = document.createElement('div');
            div.className = `log-line ${className}`; div.innerText = text;
            box.appendChild(div);
            if (scroll) box.scrollTop = box.scrollHeight;
        }
    </script>
</body>
</html>
"""

# --- الوظائف ---

def generate_numbers_func(country, count):
    numbers = []
    config = COUNTRIES[country]
    for _ in range(count):
        prefix = random.choice(config["prefixes"])
        rest_length = config["length"] - len(prefix)
        rest = "".join(random.choices(string.digits, k=rest_length))
        numbers.append(f"{config['code']}{prefix}{rest}")
    return numbers

def process_apify(numbers):
    global current_status, logs, valid_numbers, stats
    if not APIFY_TOKEN:
        logs.append("❌ خطأ: لم يتم تعيين APIFY_API_TOKEN.")
        current_status = "idle"; return
    
    logs.append(f"[*] جاري إرسال {len(numbers)} رقم إلى محرك الفحص...")
    
    # تقسيم الأرقام إلى دفعات صغيرة لتجنب فشل الطلبات الكبيرة
    chunk_size = 20
    chunks = [numbers[i:i + chunk_size] for i in range(0, len(numbers), chunk_size)]
    
    for idx, chunk in enumerate(chunks):
        logs.append(f"[*] جاري فحص الدفعة {idx+1} من {len(chunks)} (عدد: {len(chunk)})...")
        
        url = f"https://api.apify.com/v2/acts/vtrdev~whatsapp-number-validator/run-sync-get-dataset-items?token={APIFY_TOKEN}"
        payload = {"phone_numbers": chunk}
        
        try:
            response = requests.post(url, json=payload, timeout=120)
            if response.status_code in [200, 201]:
                data = response.json()
                if not data:
                    logs.append(f"⚠️ الدفعة {idx+1} رجعت فارغة من السيرفر.")
                
                for item in data:
                    if "phone" in item and "hasWhatsapp" in item:
                        phone = item["phone"]; is_valid = item["hasWhatsapp"]
                        stats["total"] += 1
                        if is_valid:
                            logs.append(f"✅ مسجل: {phone}"); valid_numbers.append(phone); stats["valid"] += 1
                        else:
                            logs.append(f"❌ غير مسجل: {phone}"); stats["invalid"] += 1
            else:
                logs.append(f"❌ خطأ في الدفعة {idx+1} (كود: {response.status_code}): {response.text[:100]}")
        except Exception as e:
            logs.append(f"❌ خطأ في الاتصال بالدفعة {idx+1}: {str(e)[:100]}")
            
        time.sleep(2)
        
    logs.append("--- اكتملت عملية الفحص بنجاح ---")
    current_status = "idle"

# --- وظائف الإرسال الجماعي ---

def process_bulk_send(message):
    global send_status, send_logs, send_progress
    send_status = "running"
    send_logs.clear()
    send_progress = {"current": 0, "total": len(valid_numbers), "success": 0, "failed": 0}
    
    if not WASERVIX_KEY:
        send_logs.append("❌ خطأ: لم يتم تعيين WASERVIX_API_KEY في إعدادات Render.")
        send_status = "idle"
        return

    send_logs.append(f"[*] بدء إرسال الرسائل إلى {len(valid_numbers)} رقم...")

    for number in valid_numbers:
        clean_number = number.replace("+", "").strip()
        send_logs.append(f"[*] جاري الإرسال إلى: {number}")
        
        try:
            payload = {
                "apiKey": WASERVIX_KEY,
                "phone": clean_number,
                "message": message
            }
            response = requests.post(WASERVIX_URL, json=payload, timeout=15)
            
            if response.status_code == 200:
                send_logs.append(f"✅ نجح الإرسال إلى: {number}")
                send_progress["success"] += 1
            else:
                send_logs.append(f"❌ فشل الإرسال إلى: {number} (كود: {response.status_code})")
                send_progress["failed"] += 1
                
        except Exception as e:
            send_logs.append(f"❌ خطأ في الاتصال للرقم {number}: {str(e)[:50]}")
            send_progress["failed"] += 1

        send_progress["current"] += 1
        
        if send_progress["current"] % 10 == 0:
            send_logs.append(f"--- تم إرسال {send_progress['current']} من أصل {send_progress['total']} ---")
            if len(send_logs) > 50: send_logs.pop(0)

        delay = random.uniform(4, 9)
        time.sleep(delay)

    send_status = "idle"
    send_logs.append(f"✅ اكتملت عملية الإرسال. (نجح: {send_progress['success']} | فشل: {send_progress['failed']})")

# --- مسارات Flask ---

@app.route('/')
def index():
    if not session.get('logged_in'): return redirect(url_for('login'))
    return render_template_string(DASHBOARD_TEMPLATE, countries=COUNTRIES)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] == 'As3ad' and request.form['password'] == 'As3ad':
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            error = "بيانات الدخول غير صحيحة."
    return render_template_string(LOGIN_TEMPLATE, error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/api/generate', methods=['POST'])
def generate_api():
    global generated_numbers, logs, stats
    data = request.json
    country = data.get('country'); count = int(data.get('count', 10))
    generated_numbers = generate_numbers_func(country, count)
    logs.clear(); stats = {"total": 0, "valid": 0, "invalid": 0}
    logs.append(f"[*] تم توليد {count} رقم لدولة {COUNTRIES[country]['ar']}.")
    return {"count": len(generated_numbers)}

@app.route('/api/check', methods=['POST'])
def check_api():
    global current_status, logs, stats, valid_numbers
    data = request.json
    specific = data.get('specific', '').strip()
    if current_status == "running": return {"error": "العملية قيد التشغيل"}, 400
    
    logs.clear(); stats = {"total": 0, "valid": 0, "invalid": 0}; current_status = "running"
    valid_numbers.clear()
    
    if specific:
        numbers = [specific]; logs.append(f"[>] جاري فحص رقم محدد: {specific}")
    else:
        numbers = generated_numbers; logs.append(f"[>] جاري فحص {len(numbers)} رقم...")
        
    threading.Thread(target=process_apify, args=(numbers,)).start()
    return {"status": "started"}

@app.route('/api/status')
def status_api():
    return {"status": current_status, "logs": logs, "stats": stats}

@app.route('/api/download')
def download_api():
    if not valid_numbers: return "لا توجد أرقام ناجحة.", 404
    output = io.StringIO()
    for num in valid_numbers: output.write(f"{num}\n")
    return Response(output.getvalue(), mimetype="text/plain", headers={"Content-Disposition": "attachment;filename=valid_numbers.txt"})

@app.route('/api/valid-count')
def valid_count():
    return {"count": len(valid_numbers)}

@app.route('/api/send-bulk', methods=['POST'])
def send_bulk_api():
    global send_status
    data = request.json
    message = data.get('message', '').strip()
    
    if not valid_numbers:
        return {"error": "لا توجد أرقام صالحة للإرسال. قم بالفحص أولاً."}, 400
    if not message:
        return {"error": "الرسالة فارغة."}, 400
    if send_status == "running":
        return {"error": "عملية إرسال قيد التنفيذ بالفعل."}, 400
        
    threading.Thread(target=process_bulk_send, args=(message,)).start()
    return {"status": "started"}

@app.route('/api/send-status')
def send_status_api():
    return {"status": send_status, "progress": send_progress, "logs": send_logs}

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
