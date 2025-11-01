import os
import hashlib
import secrets
from flask import Flask, render_template_string, request, redirect, session, jsonify
from datetime import datetime, timedelta
import requests
from database import (
    get_file_by_short_link_id, create_view_record, increment_file_views,
    check_recent_view, calculate_earnings, update_user_balance, get_ad_codes
)
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

@app.after_request
def add_ngrok_skip_header(response):
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response
def get_base_url():
    replit_domains = os.getenv('REPLIT_DOMAINS')
    if replit_domains:
        domains = replit_domains.split(',')
        return f"https://{domains[0]}"
    return os.getenv('BASE_URL', 'http://localhost:5000')

BASE_URL = get_base_url()
BOT_USERNAME = os.getenv('BOT_USERNAME', 'YourBot').lstrip('@')

rate_limit_store = {}


def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr or '0.0.0.0'


def get_country_from_ip(ip):
    if ip in ['127.0.0.1', '0.0.0.0', 'localhost']:
        return 'OTHER'
    
    try:
        response = requests.get(f'https://ipapi.co/{ip}/json/', timeout=3)
        if response.status_code == 200:
            data = response.json()
            return data.get('country_code', 'OTHER')
    except:
        pass
    
    return 'OTHER'


def check_rate_limit(ip, max_requests=10, window_minutes=5):
    now = datetime.utcnow()
    
    if ip not in rate_limit_store:
        rate_limit_store[ip] = []
    
    rate_limit_store[ip] = [
        timestamp for timestamp in rate_limit_store[ip]
        if now - timestamp < timedelta(minutes=window_minutes)
    ]
    
    if len(rate_limit_store[ip]) >= max_requests:
        return False
    
    rate_limit_store[ip].append(now)
    return True


def generate_token(file_id, page_num):
    data = f"{file_id}-{page_num}-{app.secret_key}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]


def verify_token(file_id, page_num, token):
    expected = generate_token(file_id, page_num)
    return token == expected


PAGE_1_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>File Access - Step 1</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .banner-ad {
            max-width: 728px;
            width: 100%;
            margin: 20px auto;
            min-height: 90px;
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .native-ad {
            max-width: 500px;
            width: 100%;
            margin: 20px auto;
            min-height: 120px;
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 500px;
            width: 100%;
            text-align: center;
            position: relative;
            z-index: 10;
        }
        h1 { color: #333; margin-bottom: 20px; font-size: 28px; }
        p { color: #666; margin-bottom: 30px; line-height: 1.6; }
        .timer {
            font-size: 48px;
            font-weight: bold;
            color: #667eea;
            margin: 30px 0;
        }
        .btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 15px 40px;
            font-size: 18px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            text-decoration: none;
            display: inline-block;
        }
        .btn:hover { background: #5568d3; transform: translateY(-2px); }
        .btn:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }
        .step-indicator {
            color: #999;
            font-size: 14px;
            margin-bottom: 20px;
        }
    </style>
    
    <!-- Adsterra Popunder Ad -->
    <script type="text/javascript">
        // Add your Adsterra Popunder code here
        // atOptions = {
        //     'key' : 'YOUR_POPUNDER_KEY',
        //     'format' : 'iframe',
        //     'height' : 90,
        //     'width' : 728,
        //     'params' : {}
        // };
    </script>
    <!-- <script type="text/javascript" src="//www.highperformanceformat.com/YOUR_KEY/invoke.js"></script> -->
</head>
<body>
    <!-- Banner Ad - Top -->
    <div class="banner-ad">
        <!-- Add your Adsterra Banner code here -->
        <!-- Replace this comment with your 728x90 Banner ad code -->
    </div>
    
    <!-- Native Banner Ad -->
    <div class="native-ad">
        <!-- Add your Adsterra Native Banner code here -->
        <!-- Replace this comment with your Native Banner ad code -->
    </div>
    
    <div class="container">
        <div class="step-indicator">Step 1 of 4</div>
        <h1>🔐 Accessing Your File</h1>
        <p>Please wait while we prepare your download link...</p>
        <div class="timer" id="timer">15</div>
        <button class="btn" id="continueBtn" disabled>Continue</button>
    </div>
    
    <!-- Banner Ad - Bottom -->
    <div class="banner-ad">
        <!-- Add your Adsterra Banner code here -->
        <!-- Replace this comment with your 728x90 Banner ad code -->
    </div>
    
    <script>
        let timeLeft = 15;
        const timerEl = document.getElementById('timer');
        const btn = document.getElementById('continueBtn');
        
        const countdown = setInterval(() => {
            timeLeft--;
            timerEl.textContent = timeLeft;
            
            if (timeLeft <= 0) {
                clearInterval(countdown);
                btn.disabled = false;
                btn.onclick = () => {
                    window.location.href = '{{ next_url }}';
                };
            }
        }, 1000);
    </script>
    
    <!-- Adsterra Social Bar -->
    <script type="text/javascript">
        // Add your Adsterra Social Bar code here
        // atOptions = {
        //     'key' : 'YOUR_SOCIAL_BAR_KEY',
        //     'format' : 'iframe',
        //     'height' : 50,
        //     'width' : 320,
        //     'params' : {}
        // };
    </script>
    <!-- <script type="text/javascript" src="//www.highperformanceformat.com/YOUR_KEY/invoke.js"></script> -->
</body>
</html>
'''

PAGE_2_TEMPLATE = PAGE_1_TEMPLATE.replace('Step 1 of 4', 'Step 2 of 4').replace('🔐 Accessing', '⏳ Preparing')

# Page 3 template with smartlink trigger
PAGE_3_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>File Access - Step 3</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .banner-ad {
            max-width: 728px;
            width: 100%;
            margin: 20px auto;
            min-height: 90px;
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .native-ad {
            max-width: 500px;
            width: 100%;
            margin: 20px auto;
            min-height: 120px;
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 500px;
            width: 100%;
            text-align: center;
            position: relative;
            z-index: 10;
        }
        h1 { color: #333; margin-bottom: 20px; font-size: 28px; }
        p { color: #666; margin-bottom: 30px; line-height: 1.6; }
        .timer {
            font-size: 48px;
            font-weight: bold;
            color: #667eea;
            margin: 30px 0;
        }
        .btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 15px 40px;
            font-size: 18px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            text-decoration: none;
            display: inline-block;
        }
        .btn:hover { background: #5568d3; transform: translateY(-2px); }
        .btn:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }
        .step-indicator {
            color: #999;
            font-size: 14px;
            margin-bottom: 20px;
        }
    </style>
    
    <!-- Adsterra Popunder -->
    <script type="text/javascript">
        <!-- Add your Adsterra Popunder code here -->
    </script>
</head>
<body>
    <!-- Banner Ad - Top -->
    <div class="banner-ad">
        <!-- Add your Adsterra Banner code here -->
        <!-- Replace this comment with your 728x90 Banner ad code -->
    </div>
    
    <!-- Native Banner Ad -->
    <div class="native-ad">
        <!-- Add your Adsterra Native Banner code here -->
        <!-- Replace this comment with your Native Banner ad code -->
    </div>
    
    <div class="container">
        <div class="step-indicator">Step 3 of 4</div>
        <h1>📦 Loading Your File</h1>
        <p>Please wait while we prepare your download link...</p>
        <div class="timer" id="timer">15</div>
        <button class="btn" id="continueBtn" disabled>Continue</button>
    </div>
    
    <!-- Banner Ad - Bottom -->
    <div class="banner-ad">
        <!-- Add your Adsterra Banner code here -->
        <!-- Replace this comment with your 728x90 Banner ad code -->
    </div>
    
    <script>
        let timeLeft = 15;
        const timerEl = document.getElementById('timer');
        const btn = document.getElementById('continueBtn');
        const smartlinkUrl = '{{ smartlink_url }}';
        
        const countdown = setInterval(() => {
            timeLeft--;
            timerEl.textContent = timeLeft;
            
            if (timeLeft <= 0) {
                clearInterval(countdown);
                btn.disabled = false;
                btn.onclick = () => {
                    // Open smartlink in new window/tab if URL is provided
                    if (smartlinkUrl && smartlinkUrl !== '') {
                        window.open(smartlinkUrl, '_blank');
                    }
                    // Redirect to next page after short delay
                    setTimeout(() => {
                        window.location.href = '{{ next_url }}';
                    }, 100);
                };
            }
        }, 1000);
    </script>
    
    <!-- Adsterra Social Bar -->
    <script type="text/javascript">
        <!-- Add your Adsterra Social Bar code here -->
    </script>
</body>
</html>
'''

PAGE_4_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>File Ready!</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .banner-ad {
            max-width: 728px;
            width: 100%;
            margin: 20px auto;
            min-height: 90px;
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .native-ad {
            max-width: 500px;
            width: 100%;
            margin: 20px auto;
            min-height: 120px;
            background: rgba(255,255,255,0.1);
            border-radius: 8px;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 500px;
            width: 100%;
            text-align: center;
            position: relative;
            z-index: 10;
        }
        h1 { color: #333; margin-bottom: 20px; font-size: 28px; }
        p { color: #666; margin-bottom: 30px; line-height: 1.6; }
        .timer {
            font-size: 48px;
            font-weight: bold;
            color: #11998e;
            margin: 30px 0;
        }
        .btn {
            background: #11998e;
            color: white;
            border: none;
            padding: 15px 40px;
            font-size: 18px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            text-decoration: none;
            display: inline-block;
        }
        .btn:hover { background: #0e7d73; transform: translateY(-2px); }
        .btn:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }
        .step-indicator {
            color: #999;
            font-size: 14px;
            margin-bottom: 20px;
        }
    </style>
    
    <!-- Adsterra Smartlink -->
    <script type="text/javascript">
        // Add your Adsterra Smartlink code here
        // atOptions = {
        //     'key' : 'YOUR_SMARTLINK_KEY',
        //     'format' : 'iframe',
        //     'height' : 250,
        //     'width' : 300,
        //     'params' : {}
        // };
    </script>
    <!-- <script type="text/javascript" src="//www.highperformanceformat.com/YOUR_KEY/invoke.js"></script> -->
</head>
<body>
    <!-- Banner Ad - Top -->
    <div class="banner-ad">
        <!-- Add your Adsterra Banner code here -->
        <!-- Replace this comment with your 728x90 Banner ad code -->
    </div>
    
    <!-- Native Banner Ad -->
    <div class="native-ad">
        <!-- Add your Adsterra Native Banner code here -->
        <!-- Replace this comment with your Native Banner ad code -->
    </div>
    
    <div class="container">
        <div class="step-indicator">Step 4 of 4</div>
        <h1>✅ File Ready!</h1>
        <p>Your file is ready to download. Click the button below to get your file.</p>
        <div class="timer" id="timer">5</div>
        <button class="btn" id="getBtn" disabled>Get Link</button>
    </div>
    
    <!-- Banner Ad - Bottom -->
    <div class="banner-ad">
        <!-- Add your Adsterra Banner code here -->
        <!-- Replace this comment with your 728x90 Banner ad code -->
    </div>
    
    <script>
        let timeLeft = 5;
        const timerEl = document.getElementById('timer');
        const btn = document.getElementById('getBtn');
        const smartlinkUrl = '{{ smartlink_url }}';
        
        const countdown = setInterval(() => {
            timeLeft--;
            timerEl.textContent = timeLeft;
            
            if (timeLeft <= 0) {
                clearInterval(countdown);
                btn.disabled = false;
                btn.onclick = () => {
                    // Open smartlink in new window/tab if URL is provided
                    if (smartlinkUrl && smartlinkUrl !== '') {
                        window.open(smartlinkUrl, '_blank');
                    }
                    // Redirect to bot after short delay
                    setTimeout(() => {
                        window.location.href = '{{ bot_url }}';
                    }, 100);
                };
            }
        }, 1000);
    </script>
    
    <!-- Adsterra Social Bar -->
    <script type="text/javascript">
        // Add your Adsterra Social Bar code here
        // atOptions = {
        //     'key' : 'YOUR_SOCIAL_BAR_KEY',
        //     'format' : 'iframe',
        //     'height' : 50,
        //     'width' : 320,
        //     'params' : {}
        // };
    </script>
    <!-- <script type="text/javascript" src="//www.highperformanceformat.com/YOUR_KEY/invoke.js"></script> -->
</body>
</html>
'''


@app.route('/')
def index():
    return '''
    <html>
    <head>
        <title>File Monetization Bot</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .content {
                text-align: center;
                padding: 40px;
            }
            h1 { font-size: 48px; margin-bottom: 20px; }
            p { font-size: 20px; margin-bottom: 30px; }
            a {
                background: white;
                color: #667eea;
                padding: 15px 30px;
                border-radius: 8px;
                text-decoration: none;
                font-weight: bold;
                display: inline-block;
                transition: all 0.3s;
            }
            a:hover { transform: scale(1.05); }
        </style>
    </head>
    <body>
        <div class="content">
            <h1>📁 File Monetization Bot</h1>
            <p>Upload files and earn money from every download!</p>
            <a href="https://t.me/''' + BOT_USERNAME + '''">Start Bot</a>
        </div>
    </body>
    </html>
    '''


@app.route('/download/<short_link_id>')
def download_page(short_link_id):
    ip = get_client_ip()
    
    if not check_rate_limit(ip):
        return 'Rate limit exceeded. Please try again later.', 429
    
    file_record = get_file_by_short_link_id(short_link_id)
    if not file_record:
        return 'File not found', 404
    
    if check_recent_view(short_link_id, ip):
        return 'You recently viewed this file. Please wait before trying again.', 429
    
    token = generate_token(short_link_id, 1)
    session['short_link_id'] = short_link_id
    session['started_at'] = datetime.utcnow().isoformat()
    
    next_url = f'/page1/{short_link_id}?token={token}'
    return redirect(next_url)


@app.route('/page1/<short_link_id>')
def page1(short_link_id):
    token = request.args.get('token')
    if not verify_token(short_link_id, 1, token):
        return 'Invalid access token', 403
    
    next_token = generate_token(short_link_id, 2)
    next_url = f'/page2/{short_link_id}?token={next_token}'
    
    ad_codes = get_ad_codes()
    template = PAGE_1_TEMPLATE
    template = template.replace('<!-- Add your Adsterra Popunder code here -->', ad_codes.get('popunder', ''))
    template = template.replace('<!-- Add your Adsterra Banner code here -->', ad_codes.get('banner', ''))
    template = template.replace('<!-- Add your Adsterra Native Banner code here -->', ad_codes.get('native', ''))
    template = template.replace('<!-- Add your Adsterra Social Bar code here -->', ad_codes.get('social_bar', ''))
    
    return render_template_string(template, next_url=next_url)


@app.route('/page2/<short_link_id>')
def page2(short_link_id):
    token = request.args.get('token')
    if not verify_token(short_link_id, 2, token):
        return 'Invalid access token', 403
    
    next_token = generate_token(short_link_id, 3)
    next_url = f'/page3/{short_link_id}?token={next_token}'
    
    ad_codes = get_ad_codes()
    template = PAGE_2_TEMPLATE
    template = template.replace('<!-- Add your Adsterra Popunder code here -->', ad_codes.get('popunder', ''))
    template = template.replace('<!-- Add your Adsterra Banner code here -->', ad_codes.get('banner', ''))
    template = template.replace('<!-- Add your Adsterra Native Banner code here -->', ad_codes.get('native', ''))
    template = template.replace('<!-- Add your Adsterra Social Bar code here -->', ad_codes.get('social_bar', ''))
    
    return render_template_string(template, next_url=next_url)


@app.route('/page3/<short_link_id>')
def page3(short_link_id):
    token = request.args.get('token')
    if not verify_token(short_link_id, 3, token):
        return 'Invalid access token', 403
    
    next_token = generate_token(short_link_id, 4)
    next_url = f'/page4/{short_link_id}?token={next_token}'
    
    ad_codes = get_ad_codes()
    smartlink_url = ad_codes.get('smartlink', '')
    
    template = PAGE_3_TEMPLATE
    template = template.replace('<!-- Add your Adsterra Popunder code here -->', ad_codes.get('popunder', ''))
    template = template.replace('<!-- Add your Adsterra Banner code here -->', ad_codes.get('banner', ''))
    template = template.replace('<!-- Add your Adsterra Native Banner code here -->', ad_codes.get('native', ''))
    template = template.replace('<!-- Add your Adsterra Social Bar code here -->', ad_codes.get('social_bar', ''))
    
    return render_template_string(template, next_url=next_url, smartlink_url=smartlink_url)


@app.route('/page4/<short_link_id>')
def page4(short_link_id):
    token = request.args.get('token')
    if not verify_token(short_link_id, 4, token):
        return 'Invalid access token', 403
    
    ip = get_client_ip()
    country = get_country_from_ip(ip)
    user_agent = request.headers.get('User-Agent', '')
    
    file_record = get_file_by_short_link_id(short_link_id)
    if file_record:
        create_view_record(short_link_id, ip, country, user_agent)
        increment_file_views(short_link_id, country)
        
        earnings = calculate_earnings(country)
        update_user_balance(file_record['uploader_id'], earnings)
    
    bot_url = f'https://t.me/{BOT_USERNAME}?start={short_link_id}'
    
    ad_codes = get_ad_codes()
    smartlink_url = ad_codes.get('smartlink', '')
    
    template = PAGE_4_TEMPLATE
    template = template.replace('<!-- Add your Adsterra Smartlink code here -->', ad_codes.get('smartlink', ''))
    template = template.replace('<!-- Add your Adsterra Banner code here -->', ad_codes.get('banner', ''))
    template = template.replace('<!-- Add your Adsterra Native Banner code here -->', ad_codes.get('native', ''))
    template = template.replace('<!-- Add your Adsterra Social Bar code here -->', ad_codes.get('social_bar', ''))
    
    return render_template_string(template, bot_url=bot_url, smartlink_url=smartlink_url)


@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.utcnow().isoformat()})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
