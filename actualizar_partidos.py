from backend.app.sync import sync_fixtures_and_metrics


if __name__ == '__main__':
    summary = sync_fixtures_and_metrics()
    updated_count = len(summary.get('updated', []))
    created_count = len(summary.get('created', []))
    error_count = len(summary.get('errors', []))
    print(
        f"Partidos actualizados: {updated_count}. "
        f"Partidos creados: {created_count}. "
        f"Errores: {error_count}."
    )
