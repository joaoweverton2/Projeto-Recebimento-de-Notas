#!/usr/bin/env bash

# Inicia a aplicação Gunicorn na porta fornecida pelo Render
# O Render define a variável de ambiente PORT automaticamente
exec gunicorn --bind 0.0.0.0:${PORT:-5000} main:app


