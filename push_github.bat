@echo off
REM ============================================================================
REM  Script de push GitHub - devoir de reassurance
REM  ----------------------------------------------------------------------------
REM  AVANT D'EXECUTER :
REM   1) Cree un nouveau repo (vide, sans README) sur https://github.com/new
REM   2) Remplace ci-dessous l'URL par celle de ton nouveau repo
REM   3) Double-clique sur ce fichier (ou execute-le depuis CMD)
REM ============================================================================

REM === A MODIFIER : URL HTTPS DE TON NOUVEAU REPO ==============================
set REPO_URL=https://github.com/steve-gerald/reassurance-xl-mtpl-pricing.git
REM ============================================================================

cd /d "%~dp0"
echo.
echo === Repertoire courant : %CD%
echo === Repo distant       : %REPO_URL%
echo.

REM Configuration Git (si pas deja faite)
git config user.name >nul 2>&1
if errorlevel 1 (
    echo Configuration de Git ...
    git config --global user.name "Steve"
    git config --global user.email "vanessandjiki0@gmail.com"
)

REM Init du repo si necessaire
if not exist ".git" (
    echo Initialisation du depot Git ...
    git init
    git branch -M main
)

REM Stage + commit
echo Ajout des fichiers ...
git add .
git commit -m "Devoir de reassurance XL MTPL - pricing complet" || echo  (rien a commiter)

REM Ajout du remote si pas deja present
git remote get-url origin >nul 2>&1
if errorlevel 1 (
    echo Configuration du remote origin ...
    git remote add origin %REPO_URL%
) else (
    echo Mise a jour de l URL du remote origin ...
    git remote set-url origin %REPO_URL%
)

REM Push
echo Push vers GitHub ...
git push -u origin main

echo.
echo === Termine. Va voir ton repo sur GitHub.
pause
