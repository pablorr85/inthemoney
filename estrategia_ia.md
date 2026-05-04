# Evolución a Agente de IA Financiero

Dar el salto de un bot "basado en reglas fijas" (como el cruce de medias) a un **Agente de IA Financiero** es el siguiente gran nivel en el trading algorítmico.

Aquí se detalla la radiografía de **cómo se estructuraría esta nueva arquitectura** y qué piezas del código actual tendríamos que cambiar para lograrlo.

### 1. Cambio de Paradigma: Del "If-Else" al "Prompting"
Actualmente, nuestro cerebro es una línea de código: `if cruce_alcista and rsi < 70`. 
En la nueva versión, el cerebro será una llamada a un LLM avanzado (como Gemini, GPT-4 o Claude) estructurado como un Agente. El flujo ya no será matemático, sino analítico.

### 2. Nuevos Módulos de Recopilación de Datos (Data Gatherers)
Para que la IA pueda tomar decisiones como un experto, necesita contexto. Nuestro `main.py` pasaría a orquestar diferentes fuentes de datos:

*   **Módulo Técnico (`tech_data.py`):** Lo que ya tenemos. Descarga `yfinance`, calcula SMA, RSI, MACD, Bandas de Bollinger, soportes y resistencias. Genera un resumen numérico del estado técnico.
*   **Módulo de Sentimiento Social (`social_scraper.py`):** 
    *   **Reddit:** Usando la librería `PRAW`, buscaríamos hilos en subreddits como `r/investing`, `r/StockMarket` o `r/WallStreetBets` mencionando el ticker (ej. `$IBE` o `$AAPL`).
    *   **X (Twitter):** Usando la API de X para extraer los últimos 50 tweets relevantes y con alta interacción sobre el ticker.
*   **Módulo de Noticias (`news_fetcher.py`):** Podríamos usar la propia API de Alpaca (que incluye noticias) o servicios como Finnhub para obtener titulares de Bloomberg, Reuters, etc.

### 3. El Cerebro del Agente (`ai_analyst.py`)
Aquí es donde ocurre la magia. Crearíamos una función que recopila toda la información de los módulos anteriores, la empaqueta y se la envía al modelo de IA mediante un *Prompt* maestro.

El prompt se vería algo así:
> *"Eres un experto gestor de fondos de cobertura institucional. Tu objetivo es maximizar beneficios y minimizar riesgos.*
> *Activo a analizar: $AAPL (Apple).*
> *1. Datos Técnicos: Precio actual $175. RSI a 65. Tendencia a corto plazo bajista, pero apoyándose en la SMA de 200 días.*
> *2. Noticias recientes: 'Apple retrasa el lanzamiento de sus gafas de realidad mixta', 'Fuertes ventas de iPhone en China'.*
> *3. Sentimiento Social: Mucho miedo en Reddit por los tipos de interés, pero euforia en X por posibles anuncios de IA.*
> 
> *Analiza esta información de forma holística. Devuelve un objeto JSON con la siguiente estructura:*
> `{ "action": "BUY" | "SELL" | "HOLD", "confidence": 1-100, "reasoning": "Tu explicación analítica corta" }`"

### 4. Actualización del Bucle Principal (`main.py`)
La función `execute_daily_trading_strategy` cambiaría radicalmente. En lugar de evaluar el cruce de medias, haría esto:

1. Reúne el contexto técnico (pandas).
2. Reúne el contexto social y de noticias.
3. Llama a `ai_analyst.get_decision(ticker, contexto)`.
4. Recibe el JSON de la IA.
5. Ejecuta la orden:
   * `if decision['action'] == 'BUY' and decision['confidence'] > 80:` -> Lanza la orden a Alpaca.
   * `if decision['action'] == 'SELL':` -> Cierra la posición.

### 5. Los grandes retos a tener en cuenta
Si decidimos ir por este camino, tendremos que enfrentarnos a estos desafíos:

*   **Límites y Costes de API:** Leer Reddit y llamar a un modelo de IA potente para más de 50 tickers cada hora puede consumir tokens y llamadas a API rápidamente. Seguramente tendríamos que reducir la frecuencia (ej. ejecutarlo solo a la apertura y al cierre).
*   **Alucinaciones de la IA:** A veces el modelo puede decir "BUY" basándose en una noticia falsa o una interpretación errónea. Habría que poner "guardarraíles" rígidos en el código (por ejemplo: "Aunque la IA diga BUY, si el RSI está por encima de 85, anula la orden para evitar comprar en sobrecompra extrema").
*   **Velocidad:** Las llamadas a LLMs pueden tardar varios segundos. Procesar todo el IBEX y Wall Street podría tardar un par de minutos, aunque para *swing trading* diario esto no supone ningún problema.
