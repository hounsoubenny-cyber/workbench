#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Sep  4 14:31:25 2026
@author: hounsousamuel
"""
import sys
import time
import webbrowser


def run_api():
    from workbench.products.mediakit.api.main_api import (
        start, app, start_config
    )
    from workbench.wb_utils.signal_manager import signal_manager

    thread, server = start(app, start_config=start_config)
    thread.start()
    time.sleep(2)

    def signal_handler(sig, frame):
        print('Signal envoyé : ', sig)
        server.should_exit = True
        thread.join(2)
        sys.exit(0)

    signal_manager(signal_handler)

    while not getattr(server, "started", False):
        continue

    port = start_config.port
    url = f"http://127.0.0.1:{port}"

    print('API lancé à : ', time.ctime())
    print(f'WORKBENCH_PORT={port}', flush=True)
    print(f'🌐 Ouverture de {url} dans le navigateur par défaut...')

    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"⚠️ Impossible d'ouvrir le navigateur automatiquement : {e!r}")
        print(f"👉 Ouvrez manuellement : {url}")

    start_time = time.time()
    while True:
        try:
            time.sleep(1)
            elapsed = time.time() - start_time
            print(
                f'API lancé depuis :  {elapsed:.2f} '
                f'{"seconde" if elapsed < 2 else "secondes"} '
                f'({elapsed / 60:.2f} {"minute" if elapsed / 60 < 2 else "minutes"})',
                end="\r",
            )
        except KeyboardInterrupt:
            print('Interruption , sortie !')
            break
        except Exception:
            break

    print('Fermeture API à : ', time.ctime())


if __name__ == '__main__':
    try:
        import nest_asyncio
        from workbench.products.mediakit.api.errors import StartAppError

        nest_asyncio.apply()
        run_api()

    except StartAppError as e:
        print(f"Erreur de démarrage: {e!r}")

    except SystemExit:
        pass

    except Exception:
        raise