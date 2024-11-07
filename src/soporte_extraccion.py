from google.oauth2 import service_account
from googleapiclient.discovery import build
import pandas as pd

def crear_gsheet(carpeta_destino: str, correo: str, nombre: str, df: pd.DataFrame):
    """
    Crea un Google Sheet, lo guarda en una carpeta especificada de Google Drive, y opcionalmente rellena el Google Sheet con un DataFrame.

    Parametros:
        carpeta_destino (str): La URL o el ID de la carpeta de Google Drive donde se desea guardar el Google Sheet.
        correo (str): Dirección de correo electrónico del usuario con el que se desea compartir el Google Sheet.
        nombre (str): Nombre del Google Sheet que se va a crear.
        df (pandas.DataFrame, opcional): DataFrame con los datos que se van a insertar en el Google Sheet. Por defecto es None.

    Lanza:
        Exception: Si ocurre un error al acceder a la carpeta, mover el archivo o en el proceso general.

    Retorna:
        str: url del archivo

    Ejemplo:
        url_archivo = crear_gsheet(carpeta_destino, correo, nombre, df)

    """

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

    # Autenticar usando el archivo JSON de la cuenta de servicio
    creds = service_account.Credentials.from_service_account_file(
        "../credentials.json", scopes=SCOPES
    )

    try:
        
        # Crear un nuevo servicio de la API de Google Drive
        drive_service = build("drive", "v3", credentials=creds)

        # Especificar el ID de la carpeta en la que deseas guardar el archivo
        id_carpeta_destino = carpeta_destino.split("/")[-1]  # Reemplazar con el ID real de la carpeta

        # Verificar si la cuenta de servicio tiene acceso a la carpeta especificada
        try:
            folder = drive_service.files().get(fileId=id_carpeta_destino, fields="id, name").execute()
            print(f"Carpeta encontrada: {folder.get('name')} (ID: {folder.get('id')})")
        except Exception as e:
            print(f"Error: No se puede acceder a la carpeta. Asegúrate de que la cuenta de servicio tenga permisos de acceso. Error detallado: {e}")
            raise  # Detiene el script si no se puede acceder a la carpeta

        # Crear un nuevo servicio de la API de Google Sheets
        sheets_service = build("sheets", "v4", credentials=creds)

        # Crear el Google Sheet
        spreadsheet = {
            "properties": {
                "title": nombre
            }
        }
        spreadsheet = sheets_service.spreadsheets().create(body=spreadsheet, fields="spreadsheetId").execute()
        spreadsheet_id = spreadsheet.get("spreadsheetId")
        print(f"Spreadsheet ID: {spreadsheet_id}")

        # Intentamos mover el archivo a la carpeta especificada
        try:
            drive_service.files().update(
                fileId=spreadsheet_id,
                addParents=id_carpeta_destino,
                removeParents="root",  # Esto remueve el archivo de la carpeta raíz (Mi unidad)
                fields="id, parents"
            ).execute()
            print(f"El archivo ha sido movido a la carpeta con ID: {id_carpeta_destino}")
        except Exception as e:
            print(f"Error al mover el archivo a la carpeta: {e}")
            raise  # Detener el script si no se puede mover el archivo

        # Tenemos que sustituir los nulos por strings para poder meterlos en el archivo que hemos creado
        df.fillna("NaN", inplace=True)

        # Normalizamos valores a introducir
        valores = [df.columns.values.tolist()] + df.values.tolist()
        body = {
            "values": valores
        }

        # Le indicamos desde que celda insertamos datos
        sheet_range = "A1"

        # Volcamos los archivos en el documento
        result = (
            sheets_service.spreadsheets()
            .values()
            .update(
                spreadsheetId=spreadsheet_id,
                range=sheet_range,
                valueInputOption="RAW",
                body=body,
            )
            .execute()
        )

        # En caso de ejecutarse correctamente mostramos este mensaje con el número de celdas modificadas
        print(f"{result.get('updatedCells')} celdas actualizadas.")

        # Comparto el archivo con el correo indicado
        drive_service.permissions().create(
            fileId=spreadsheet_id,
            body={
                "type": "user",
                "role": "writer",
                "emailAddress": correo
            },
        ).execute()

        # Retornamos la URL del archivo para saber que documento es. Aunque también podemos ir a la cuenta de correo especificada y ver allí el nuevo archivo.
        url_archivo = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        return url_archivo
            
    except Exception as e:
        print(f"Error: {e}")
