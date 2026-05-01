## Esqueleto
```text
frontend/
├── index.html          ← Login (misma página, dos secciones: user | admin)
├── pages/
│   ├── chat.html       ← Chat del usuario normal
│   └── admin.html      ← Panel admin
├── css/
│   └── style.css       ← Único archivo, estilos globales
└── js/
    ├── config.js       ← URL base de la API (/api/v1)
    ├── api.js          ← Wrapper de fetch(): get(), post(), put(), del()
    ├── auth.js         ← login(), logout(), checkSession()
    ├── chat.js         ← Lógica del chat
    └── admin.js        ← Lógica del panel admin
```