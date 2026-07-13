import { defineAuth } from '@aws-amplify/backend'

export const auth = defineAuth({
  loginWith: {
    email: {
      verificationEmailStyle: 'CODE',
      verificationEmailSubject: 'Forex Trading AI — Código de verificación',
      verificationEmailBody: (createCode) =>
        `<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verificación Forex Trading AI</title>
    <style>
        body { margin: 0; padding: 0; background-color: #0f172a; font-family: 'Helvetica', 'Arial', sans-serif; }
        table { border-collapse: collapse !important; }
    </style>
</head>
<body>
    <table border="0" cellpadding="0" cellspacing="0" width="100%">
        <tr>
            <td bgcolor="#0f172a" align="center" style="padding: 40px 10px;">
                <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px; background-color: #1e293b; border-radius: 16px; overflow: hidden; border: 1px solid #334155;">
                    <tr>
                        <td bgcolor="#0ea5e9" align="center" style="padding: 30px;">
                            <h1 style="color: #ffffff; margin: 0; font-size: 24px;">📈 Forex Trading AI</h1>
                            <p style="color: #e0f2fe; margin: 8px 0 0 0; font-size: 11px; letter-spacing: 2px; text-transform: uppercase;">Sistema de Análisis con Inteligencia Artificial</p>
                        </td>
                    </tr>
                    <tr>
                        <td align="left" style="padding: 40px 30px 20px 30px; color: #e2e8f0; font-size: 16px; line-height: 26px;">
                            <p style="margin: 0;">Hola,</p>
                            <p style="margin-top: 20px;">Para verificar tu cuenta, usa el siguiente código:</p>
                            <table border="0" cellpadding="0" cellspacing="0" width="100%" style="margin-top: 25px; background-color: #0f172a; border-radius: 8px; border: 1px solid #0ea5e9;">
                                <tr>
                                    <td style="padding: 25px; text-align: center;">
                                        <p style="margin: 0; font-size: 13px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px;">Código de verificación</p>
                                        <p style="margin: 12px 0 0 0; font-size: 36px; font-weight: bold; color: #0ea5e9; letter-spacing: 6px;">${createCode()}</p>
                                    </td>
                                </tr>
                            </table>
                            <p style="margin-top: 25px; font-size: 14px; color: #64748b;">
                                Este código expira en 24 horas. Si no solicitaste esta verificación, ignora este mensaje.
                            </p>
                        </td>
                    </tr>
                    <tr>
                        <td align="center" style="padding: 25px 30px; border-top: 1px solid #334155;">
                            <p style="margin: 0; font-size: 11px; color: #475569;">
                                © ${new Date().getFullYear()} Forex Trading AI · Herramienta de apoyo a la decisión<br>
                                <strong>No constituye asesoría financiera.</strong>
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>`,
    },
  },
  userAttributes: {
    'custom:trading_level': { dataType: 'String', mutable: true },
  },
})
