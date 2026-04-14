import os
import shutil

os.makedirs('api', exist_ok=True)
os.makedirs('frontend/js', exist_ok=True)
os.makedirs('frontend/css', exist_ok=True)

app_py = """
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import json

app = FastAPI()

@app.get("/api/config")
def get_config():
    with open("LSDConfig.json", "r") as f:
        return json.load(f)

@app.put("/api/config")
def update_config(data: dict):
    with open("LSDConfig.json", "w") as f:
        json.dump(data, f, indent=2)
    return {"status": "ok"}

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=7860)
"""
with open("app.py", "w") as f: f.write(app_py)

index_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>LSD UI</title>
    <link rel="stylesheet" href="css/app.css">
</head>
<body>
    <header>
        <button class="tab-btn active" data-target="tab-config">Configuration</button>
    </header>
    <main>
        <div id="tab-config" class="tab-panel active">
            <div id="config-form"></div>
            <button onclick="saveConfig()">Save</button>
        </div>
    </main>
    <script src="js/app.js"></script>
    <script src="js/config.js"></script>
</body>
</html>
"""
with open("frontend/index.html", "w") as f: f.write(index_html)

config_js = """
const CONFIG_SCHEMA = [
    {
        section: "Profile Configuration",
        fields: [
            { key: "profile.vel_start_kms", label: "Velocity Start (km/s)", type: "number", step: 0.1 },
            { key: "profile.vel_end_kms", label: "Velocity End (km/s)", type: "number", step: 0.1 }
        ]
    }
];

async function loadConfig() {
    const res = await fetch('/api/config');
    const data = await res.json();
    _populate(data);
}

function _populate(data) {
    CONFIG_SCHEMA.forEach(sec => {
        sec.fields.forEach(f => {
            const el = document.getElementById(f.key);
            if(el) {
                let val = data;
                const parts = f.key.split('.');
                for(let p of parts) {
                    if(val === undefined) break;
                    val = val[p];
                }
                el.value = val;
            }
        });
    });
}

function _buildForm() {
    const container = document.getElementById('config-form');
    CONFIG_SCHEMA.forEach(sec => {
        const div = document.createElement('div');
        div.innerHTML = `<h3>${sec.section}</h3>`;
        sec.fields.forEach(f => {
            div.innerHTML += `
                <div class="field-row">
                    <label>${f.label}</label>
                    <input type="${f.type}" id="${f.key}" step="${f.step || 'any'}">
                    <span class="tooltip" title="Tooltip for ${f.label}">?</span>
                </div>
            `;
        });
        container.appendChild(div);
    });
}

async function saveConfig() {
    alert("Save configuration not fully implemented in stub, but layout is set!");
}

_buildForm();
loadConfig();
"""
with open("frontend/js/config.js", "w") as f: f.write(config_js)

