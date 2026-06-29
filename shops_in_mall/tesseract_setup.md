# Tesseract OCR Setup

`pytesseract` is only a Python wrapper. The Windows Tesseract OCR application must also be installed.

## Install With Chocolatey

Open PowerShell as Administrator:

```powershell
choco install tesseract -y
```

The expected install location is:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

If PowerShell cannot find `tesseract` immediately after installation, refresh the shell:

```powershell
refreshenv
```

Or close and reopen PowerShell.

## Verify

```powershell
where.exe tesseract
tesseract --version
```

The demo script also checks common install paths directly, so it can usually work even before PATH refreshes.

