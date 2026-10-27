"""Calculadora de coste de reuniones — interfaz minimalista (tkinter).

Sin dependencias externas.
"""
import time
import tkinter as tk
import tkinter.font as tkfont

# ---------- Configuración ----------
HORAS_ANUALES = 52 * 40            # mismo supuesto que la versión original
SEGUNDOS_ANUALES = HORAS_ANUALES * 3600

BG = "#FAFAF8"
PANEL = "#FFFFFF"
TEXT = "#1A1A1A"
MUTED = "#8A8A85"
LINE = "#E6E6E1"
ACCENT = "#1A1A1A"
ALERT = "#D64545"


def elegir_fuente():
    """Primera fuente disponible de una lista de preferencias."""
    disponibles = set(tkfont.families())
    for f in ("Segoe UI", "SF Pro Display", "Helvetica Neue", "Inter", "Helvetica", "DejaVu Sans"):
        if f in disponibles:
            return f
    return "TkDefaultFont"


class Boton(tk.Label):
    """Botón plano con efecto hover."""

    def __init__(self, master, texto, comando, primario=False, **kw):
        self.primario = primario
        self.base_bg = ACCENT if primario else PANEL
        self.base_fg = "#FFFFFF" if primario else TEXT
        self.hover_bg = "#333333" if primario else "#F0F0EC"
        super().__init__(master, text=texto, bg=self.base_bg, fg=self.base_fg,
                         cursor="hand2", padx=22, pady=10,
                         highlightthickness=0 if primario else 1,
                         highlightbackground=LINE, **kw)
        self.comando = comando
        self.bind("<Enter>", lambda e: self.config(bg=self.hover_bg))
        self.bind("<Leave>", lambda e: self.config(bg=self.base_bg))
        self.bind("<Button-1>", lambda e: self.comando())

    def set_texto(self, texto):
        self.config(text=texto)


class Fila:
    """Una fila de participantes: salario anual y cantidad de personas."""

    def __init__(self, app, parent, fuente):
        self.app = app
        self.frame = tk.Frame(parent, bg=PANEL)
        self.frame.pack(fill="x", pady=4)

        self.salario = tk.StringVar()
        self.cantidad = tk.StringVar(value="1")
        for v in (self.salario, self.cantidad):
            v.trace_add("write", lambda *a: app.actualizar_tarifa())

        caja = tk.Frame(self.frame, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        caja.pack(side="left", fill="x", expand=True)
        tk.Label(caja, text="€", bg=PANEL, fg=MUTED, font=(fuente, 12)).pack(side="left", padx=(10, 0))
        self.entry = tk.Entry(caja, textvariable=self.salario, relief="flat", bg=PANEL, fg=TEXT,
                              insertbackground=TEXT, font=(fuente, 12), width=8,
                              highlightthickness=0)
        self.entry.pack(side="left", fill="x", expand=True, padx=6, pady=8)
        tk.Label(caja, text="/ año", bg=PANEL, fg=MUTED, font=(fuente, 10)).pack(side="right", padx=10)

        tk.Label(self.frame, text="×", bg=PANEL, fg=MUTED, font=(fuente, 12)).pack(side="left", padx=(10, 4))
        cajac = tk.Frame(self.frame, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        cajac.pack(side="left")
        tk.Entry(cajac, textvariable=self.cantidad, relief="flat", bg=PANEL, fg=TEXT,
                 insertbackground=TEXT, font=(fuente, 12), width=3, justify="center",
                 highlightthickness=0).pack(padx=6, pady=8)

        quitar = tk.Label(self.frame, text="✕", bg=PANEL, fg=MUTED, cursor="hand2",
                          font=(fuente, 11), padx=8)
        quitar.pack(side="left")
        quitar.bind("<Enter>", lambda e: quitar.config(fg=ALERT))
        quitar.bind("<Leave>", lambda e: quitar.config(fg=MUTED))
        quitar.bind("<Button-1>", lambda e: app.quitar_fila(self))

    @staticmethod
    def _num(txt):
        try:
            return float(txt.replace(",", ".").replace(" ", "")) if txt.strip() else 0.0
        except ValueError:
            return 0.0

    def total_anual(self):
        salario = max(self._num(self.salario.get()), 0)
        try:
            n = max(int(self.cantidad.get() or 0), 0)
        except ValueError:
            n = 0
        return salario * n, n

    def destruir(self):
        self.frame.destroy()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Coste de reunión")
        self.configure(bg=BG)
        self.geometry("860x520")
        self.minsize(700, 460)

        f = self.fuente = elegir_fuente()
        self.filas = []
        self.tarifa = 0.0          # € por segundo
        self.coste = 0.0
        self.transcurrido = 0.0
        self.corriendo = False
        self._ultimo = None

        # ---- Panel izquierdo: participantes ----
        izq = tk.Frame(self, bg=PANEL, width=380)
        izq.pack(side="left", fill="y")
        izq.pack_propagate(False)
        tk.Frame(self, bg=LINE, width=1).pack(side="left", fill="y")

        tk.Label(izq, text="Participantes", bg=PANEL, fg=TEXT,
                 font=(f, 15, "bold")).pack(anchor="w", padx=28, pady=(28, 2))
        tk.Label(izq, text="Salario anual bruto y nº de personas", bg=PANEL, fg=MUTED,
                 font=(f, 10)).pack(anchor="w", padx=28, pady=(0, 14))

        self.lista = tk.Frame(izq, bg=PANEL)
        self.lista.pack(fill="x", padx=28)

        anadir = tk.Label(izq, text="+  Añadir participante", bg=PANEL, fg=MUTED,
                          cursor="hand2", font=(f, 11))
        anadir.pack(anchor="w", padx=28, pady=14)
        anadir.bind("<Enter>", lambda e: anadir.config(fg=TEXT))
        anadir.bind("<Leave>", lambda e: anadir.config(fg=MUTED))
        anadir.bind("<Button-1>", lambda e: self.anadir_fila())

        self.resumen = tk.Label(izq, text="", bg=PANEL, fg=MUTED, font=(f, 10), justify="left")
        self.resumen.pack(side="bottom", anchor="w", padx=28, pady=24)

        # ---- Panel derecho: contador ----
        der = tk.Frame(self, bg=BG)
        der.pack(side="left", fill="both", expand=True)

        centro = tk.Frame(der, bg=BG)
        centro.place(relx=0.5, rely=0.46, anchor="center")

        tk.Label(centro, text="COSTE ACUMULADO", bg=BG, fg=MUTED,
                 font=(f, 10)).pack()
        self.lbl_coste = tk.Label(centro, text="0,00 €", bg=BG, fg=TEXT,
                                  font=(f, 56, "bold"))
        self.lbl_coste.pack(pady=(6, 0))
        self.lbl_tiempo = tk.Label(centro, text="00:00:00", bg=BG, fg=MUTED,
                                   font=(f, 22))
        self.lbl_tiempo.pack(pady=(0, 6))
        self.lbl_tarifa = tk.Label(centro, text="0,00 € por minuto", bg=BG, fg=MUTED,
                                   font=(f, 11))
        self.lbl_tarifa.pack(pady=(0, 30))

        botones = tk.Frame(centro, bg=BG)
        botones.pack()
        self.btn_inicio = Boton(botones, "Iniciar", self.alternar, primario=True, font=(f, 12))
        self.btn_inicio.pack(side="left", padx=6)
        Boton(botones, "Reiniciar", self.reiniciar, font=(f, 12)).pack(side="left", padx=6)

        tk.Label(der, text="Espacio: iniciar / pausar", bg=BG, fg="#B5B5AF",
                 font=(f, 9)).pack(side="bottom", pady=14)

        self.bind("<space>", self._tecla_espacio)
        self.anadir_fila()
        self.actualizar_tarifa()

    # ---------- Participantes ----------
    def anadir_fila(self):
        fila = Fila(self, self.lista, self.fuente)
        self.filas.append(fila)
        fila.entry.focus_set()
        self.actualizar_tarifa()

    def quitar_fila(self, fila):
        if len(self.filas) == 1:
            fila.salario.set("")
            fila.cantidad.set("1")
            return
        self.filas.remove(fila)
        fila.destruir()
        self.actualizar_tarifa()

    def actualizar_tarifa(self):
        total = personas = 0
        for fila in self.filas:
            t, n = fila.total_anual()
            total += t
            personas += n
        self.tarifa = total / SEGUNDOS_ANUALES
        self.lbl_tarifa.config(text=f"{self._eur(self.tarifa * 60)} por minuto")
        self.resumen.config(
            text=f"{personas} persona{'s' if personas != 1 else ''}\n"
                 f"Masa salarial: {self._eur(total, 0)} / año")

    # ---------- Cronómetro ----------
    def _tecla_espacio(self, event):
        if isinstance(self.focus_get(), tk.Entry):
            return
        self.alternar()

    def alternar(self):
        if self.corriendo:
            self._actualizar()   # fija el último instante
            self.corriendo = False
            self.btn_inicio.set_texto("Reanudar")
        else:
            self.corriendo = True
            self._ultimo = time.monotonic()
            self.btn_inicio.set_texto("Pausar")
            self._tick()
        self.focus_set()

    def reiniciar(self):
        self.corriendo = False
        self.coste = 0.0
        self.transcurrido = 0.0
        self.btn_inicio.set_texto("Iniciar")
        self._pintar()

    def _actualizar(self):
        ahora = time.monotonic()
        dt = ahora - self._ultimo
        self._ultimo = ahora
        self.transcurrido += dt
        self.coste += dt * self.tarifa   # acumula con la tarifa vigente (admite cambios en directo)

    def _tick(self):
        if not self.corriendo:
            return
        self._actualizar()
        self._pintar()
        self.after(50, self._tick)

    def _pintar(self):
        t = int(self.transcurrido)
        self.lbl_tiempo.config(text=f"{t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d}")
        self.lbl_coste.config(text=self._eur(self.coste))

    @staticmethod
    def _eur(valor, decimales=2):
        s = f"{valor:,.{decimales}f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{s} €"


if __name__ == "__main__":
    App().mainloop()
