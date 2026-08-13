"""
Script de Prevencion de Suspension (Stay Awake) para Windows
Pulse Metrics - Monitoreo de Medios con IA

Mantiene el sistema activo (CPU, Red y Pantalla si se desea) para evitar que 
Windows suspenda la laptop durante el monitoreo desatendido o nocturno.
"""

import sys
import time
import os

def enable_stay_awake(keep_display_on=False):
    """
    Invoca la API de Windows SetThreadExecutionState para prevenir suspension.
    """
    if sys.platform != "win32":
        print("[!] Este script esta disenado para sistemas operativos Windows.")
        return False
    
    try:
        import ctypes
        
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ES_DISPLAY_REQUIRED = 0x00000002
        ES_AWAYMODE_REQUIRED = 0x00000040
        
        flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED
        if keep_display_on:
            flags |= ES_DISPLAY_REQUIRED
            
        res = ctypes.windll.kernel32.SetThreadExecutionState(flags)
        return res != 0
    except Exception as e:
        print(f"[!] Error al activar prevencion de suspension: {e}")
        return False

def disable_stay_awake():
    """
    Restaura la configuracion normal de energia de Windows.
    """
    if sys.platform == "win32":
        try:
            import ctypes
            ES_CONTINUOUS = 0x80000000
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        except Exception:
            pass

def main():
    os.system("cls" if os.name == "nt" else "clear")
    print("=" * 60)
    print("   PULSE METRICS - SCRIPT DE PREVENCION DE SUSPENSION")
    print("=" * 60)
    print()
    print("[*] Activando modo 'Siempre Activo' en Windows...")
    
    success = enable_stay_awake(keep_display_on=False)
    if success:
        print("[OK] Prevencion de suspension activada con exito!")
        print("     - La laptop NO se suspendera.")
        print("     - Las tareas de monitoreo e IA continuaran sin interrupcion.")
        print("     - Presiona Ctrl + C en cualquier momento para restaurar.")
    else:
        print("[!] No se pudo comunicar con el subsistema de energia de Windows.")
        
    print()
    print("-" * 60)
    
    start_time = time.time()
    try:
        while True:
            elapsed = int(time.time() - start_time)
            hours, remainder = divmod(elapsed, 3600)
            minutes, seconds = divmod(remainder, 60)
            timer_str = f"{hours:02d}h {minutes:02d}m {seconds:02d}s"
            
            print(f"\r[*] Estado: ACTIVO (Sin suspension) | Tiempo: {timer_str}", end="", flush=True)
            
            # Re-activar periodicamente cada 30 segundos como latido de seguridad
            enable_stay_awake(keep_display_on=False)
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n[*] Desactivando prevencion de suspension y restaurando energia normal...")
        disable_stay_awake()
        print("[OK] Configuracion normal de Windows restaurada. Hasta luego!")

if __name__ == "__main__":
    main()
