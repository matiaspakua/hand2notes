"""Domain-specific vocabulary that must never be spell-corrected.

These sets cover:
- Digital-transformation / business-strategy terminology
- Spanish connector words and particles frequently misread by OCR
- Common English tech terms that appear in mixed-language notes
- Obsidian / Markdown syntax tokens
"""

# Terms that must survive correction unchanged (lowercased for lookup).
DOMAIN_TERMS: frozenset[str] = frozenset({
    # ── Digital Transformation / Business strategy (ES) ──────────────────────
    "transformación", "digital", "estrategia", "estratégica", "estratégico",
    "corporativa", "corporativo", "funcional", "competitividad", "competitiva",
    "competitivo", "competencias", "posicionamiento", "diferenciación",
    "segmentación", "segmento", "nicho", "franquicia", "expansión",
    "diversificación", "internacionalización", "benchmarking",
    "stakeholders", "kpis", "kpi", "rrll", "rrhh", "ceo", "cto", "cfo",
    "marketing", "ventas", "producción", "logística", "operaciones",
    "planificación", "presupuesto", "presupuestos", "rendimiento",
    "rentabilidad", "solvencia", "liquidez", "facturación", "ebitda",
    "objetivos", "objetivo", "misión", "visión", "valores", "foda", "dafo",
    "swot", "pest", "canvas", "bmc", "ods", "rsc",
    # ── Extended business / management (ES) ────────────────────────────────────
    "empresa", "empresarial", "gestión", "negocio", "negocios", "mercado",
    "mercados", "cliente", "clientes", "proveedor", "proveedores",
    "competencia", "competidor", "competidores", "ventaja", "ventajas",
    "cadena", "valor", "modelo", "modelos", "producto", "productos",
    "servicio", "servicios", "proceso", "procesos", "proyecto", "proyectos",
    "recurso", "recursos", "humano", "humanos", "capital", "financiero",
    "inversión", "coste", "costes", "costo", "costos", "precio", "precios",
    "ingreso", "ingresos", "margen", "márgenes", "análisis", "analisis",
    "política", "políticas", "comercial", "táctica", "táctico", "técnico",
    "industria", "sector", "organización", "estructura", "departamento",
    "departamentos", "área", "áreas", "división", "divisiones", "unidad",
    "unidades", "equipo", "equipos", "liderazgo", "dirección", "gerencia",
    "administración", "gestor", "gestores", "directivo", "directivos",
    "evaluación", "indicador", "indicadores", "medición", "métrica",
    "métricas", "objetivo", "objetivos", "meta", "metas", "resultado",
    "resultados", "impacto", "eficiencia", "eficacia", "calidad",
    "innovación", "mejora", "continua", "sostenible", "sustentable",
    "corto", "plazo", "largo", "medio", "tamaño", "crecimiento",
    "desarrollo", "implementación", "ejecución", "monitoreo",
    "seguimiento", "control", "supervisión", "auditoría", "riesgo",
    "riesgos", "matriz", "portafolio", "cartera", "participación",
    "cuota", "cobertura", "penetración", "lealtad", "fidelidad",
    "satisfacción", "retención", "adquisición", "conversión",
    # ── Technology / IT ───────────────────────────────────────────────────────
    "software", "hardware", "backend", "frontend", "api", "rest", "json",
    "xml", "http", "https", "sql", "nosql", "cloud", "saas", "paas", "iaas",
    "devops", "agile", "scrum", "kanban", "sprint", "pipeline", "deployment",
    "microservicio", "microservicios", "kubernetes", "docker", "container",
    "blockchain", "iot", "ai", "ml", "ia", "bigdata", "analytics",
    "dashboard", "workflow", "framework",
    # ── Data / governance ────────────────────────────────────────────────────
    "dataset", "datahub", "datalake", "datamart", "governance",
    "metadata", "ontología", "taxonomía",
    # ── Common English words that appear in ES tech notes ───────────────────
    "plan", "business", "model", "market", "product", "service", "value",
    "chain", "network", "platform", "ecosystem", "partner", "customer",
    "user", "process", "project", "team", "roadmap", "milestone",
    # ── Obsidian / Markdown tokens ───────────────────────────────────────────
    "obsidian", "markdown", "vault", "nota", "notas",
})

# Single characters and tokens that are always kept as-is
_ALWAYS_SKIP: frozenset[str] = frozenset({"→", "←", "↑", "↓", "↔", "·", "•", "–", "—", "…"})


def is_domain_term(word: str) -> bool:
    """Return True if the word must not be corrected."""
    return word.lower() in DOMAIN_TERMS or word in _ALWAYS_SKIP
