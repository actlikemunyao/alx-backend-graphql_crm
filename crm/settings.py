INSTALLED_APPS = [
    # default Django apps...
    "django_crontab",
    "graphene_django",
    "crm",
]

GRAPHENE = {
    "SCHEMA": "crm.schema.schema"
}

CRONJOBS = [
    ('*/5 * * * *', 'crm.cron.log_crm_heartbeat'),
    ('0 */12 * * *', 'crm.cron.update_low_stock'),
]
