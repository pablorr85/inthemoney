# ¿Cómo funciona mi Bot de Inversión? (Explicación Sencilla)

Este documento explica de forma clara y sin lenguaje técnico cómo decide el bot cuándo comprar, cuándo vender y cómo cuida tu dinero. Imagina que el bot es un ayudante muy disciplinado que sigue unas reglas estrictas todos los días antes de que cierre el mercado.

---

## 1. ¿Cuándo decide COMPRAR una empresa?

Para que el bot compre acciones de una empresa, tienen que alinearse **tres planetas** al mismo tiempo:

### Planeta A: "La tendencia acaba de mejorar" (El Cruce Dorado)
El bot dibuja mentalmente dos líneas para cada empresa:
* **La línea rápida:** La media de su precio en los últimos 9 días.
* **La línea lenta:** La media de su precio en los últimos 21 días.

El bot solo presta atención cuando **la línea rápida cruza hacia arriba a la línea lenta**. Esto es una señal matemática que significa: *"Ojo, esta empresa llevaba un tiempo estancada o bajando, pero de repente está cogiendo fuerza y empieza a subir"*. 

### Planeta B: "Aún estamos a tiempo" (El Filtro RSI < 75)
A veces, una empresa sube tan rápido que sale en las noticias y todo el mundo la compra por avaricia. El bot tiene un sensor llamado RSI que mide si la acción está "sobrecalentada" (demasiado cara por la euforia). 
* Si la empresa ha subido demasiado rápido de golpe (RSI mayor a 75), el bot dice: *"Ya es tarde, no voy a comprar en la cima"*, y la deja pasar.

### Planeta C: "Hacienda me lo permite" (Protección de 2 meses)
Si el bot compró esta misma empresa hace poco y la tuvo que vender con pérdidas, **se prohíbe a sí mismo volver a comprarla durante 60 días**. Esto lo hace para cumplir con la ley española y asegurarse de que puedas deducirte esa pérdida en la Declaración de la Renta sin penalizaciones. Si la venta anterior fue con ganancias, no hay problema y vuelve a comprar.

---

## 2. ¿Cuánto dinero se gasta en la compra? (El Presupuesto)

El bot tiene una regla de oro para no fundirse todo tu capital en la primera empresa que vea. Tú le configuras un **Presupuesto Máximo por Operación** (por ejemplo, 50€).

Cuando todas las condiciones anteriores se cumplen y toca comprar:
1. El bot mira qué precio tiene la empresa hoy.
2. Calcula **cuántas acciones enteras puede comprar** sin pasarse de tu presupuesto (Ej: Si vale 10€ y tu presupuesto es 50€, compra 5 acciones).
3. **¿Qué pasa si la empresa es muy cara?** Si detecta que comprar 1 sola acción de Microsoft cuesta 400€ y tu presupuesto es 50€, el bot **descarta la compra**. Es decir, se adapta a tu bolsillo.

Esto garantiza que tu dinero se divida en "porciones" iguales y tengas una cartera diversificada, en lugar de jugártelo todo a una sola carta.

---

## 3. ¿Cuándo decide VENDER?

Vender es mucho más sencillo. El bot es paciente y mantendrá las acciones compradas mientras la empresa siga en buena racha.

El único motivo por el que venderá es si ocurre un **Cruce de la Muerte**:
* Es exactamente lo contrario al momento de la compra: **La línea rápida (9 días) cruza hacia abajo a la línea lenta (21 días)**.
* Esto significa que la tendencia alcista se ha roto y la empresa está perdiendo fuerza de forma continuada.
* En ese momento, el bot vende todas las acciones para proteger las ganancias que haya conseguido, o para cortar las pérdidas antes de que la caída sea más grave.

---

## Resumen del día a día del Bot
1. Se despierta.
2. Revisa tu lista de empresas favoritas.
3. Se salta las que valen más que tu presupuesto.
4. Compra las que acaban de cambiar a una tendencia positiva y aún no están sobrecalentadas.
5. Vende las que han roto su tendencia positiva.
6. Se va a dormir.
