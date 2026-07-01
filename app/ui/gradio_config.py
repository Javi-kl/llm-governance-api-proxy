# ---- Mensajes personalizados de chat ----

BLOCK_MESSAGE = (
    "⚠️ Tu mensaje contiene información que no podemos procesar. "
    "Por favor, reformúlalo sin incluir datos sensibles."
)

PROVIDER_ERROR_MESSAGE = (
    "⚠️ El servicio no está disponible en este momento. Inténtalo de nuevo."
)

AUTH_ERROR_MESSAGE = "⚠️ No tienes sesión activa. Recarga la página e inicia sesión."


# ---- Estilo visual ----

GRADIO_CSS = """
.gradio-container {
    width: 100% !important;
    max-width: 860px !important;
    margin: 0 auto !important;
}

.chat-actions {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1rem;
}

.chat-action-link,
.chat-action-button {
    border: 1px solid #4b5563;
    border-radius: 6px;
    padding: 0.5rem 0.75rem;
    background: transparent;
    color: #00CED1;
    font-size: 0.875rem;
    font-weight: 500;
    text-decoration: none;
    cursor: pointer;
}

.chat-action-link:hover,
.chat-action-button:hover {
    background: #273447;
}

footer { display: none !important; }
"""

GRADIO_HEAD = """
<script>
(function () {
    if (!localStorage.getItem("theme")) {
        localStorage.setItem("theme", "dark");
        window.location.reload();
    }

    if (localStorage.getItem("theme") === "dark") {
        document.documentElement.classList.add("dark");
    }

    window.logoutFromChat = async function () {
        try {
            await fetch("/api/v1/auth/logout", {
                method: "POST",
                credentials: "same-origin"
            });
        } finally {
            window.location.href = "/login";
        }
    };
})();
</script>
"""
