#!/usr/bin/env python
import os
import sys

# Garantir que o script roda do diretório correto
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())

from app import app, bootstrap

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 Iniciando Prospecção CNPJ")
    print("="*60)
    
    try:
        bootstrap()
        print("\n✅ Bootstrap completado com sucesso")
        print("\n📊 Acessar em:")
        print("   - http://localhost:5000")
        print("   - http://127.0.0.1:5000")
        print("\n" + "="*60)
        print()
        
        app.run(
            host="0.0.0.0",
            port=5000,
            debug=False,
            use_reloader=False,
        )
    except Exception as e:
        print(f"\n❌ Erro ao inicializar: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
