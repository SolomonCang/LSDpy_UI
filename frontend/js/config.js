
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
