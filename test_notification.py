#!/usr/bin/env python3
"""
Script para testar a notificação WhatsApp do novo CNPJ
Uso: python test_notification.py
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

from whatsapp_sender import notify_admin_new_lead

def main():
    print("🚀 Iniciando teste de notificação...")
    print()
    
    # Dados de teste
    test_data = {
        "cnpj": "12.345.678/0001-99",
        "razao_social": "EMPRESA TESTE LTDA",
        "cidade": "São Paulo",
        "uf": "SP",
        "segmento": "Consultoria de Negócios"
    }
    
    print("📦 Dados de teste:")
    for key, value in test_data.items():
        print(f"   {key}: {value}")
    print()
    
    print("📤 Enviando notificação...")
    result = notify_admin_new_lead(**test_data)
    
    print()
    if result.get("ok"):
        print("✅ Notificação enviada com sucesso!")
        print(f"   Resposta: {result.get('data')}")
    else:
        print("❌ Erro ao enviar notificação!")
        print(f"   Erro: {result.get('error')}")
        sys.exit(1)

if __name__ == "__main__":
    main()
