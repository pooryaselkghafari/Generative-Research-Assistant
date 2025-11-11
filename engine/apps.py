from django.apps import AppConfig

class EngineConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'engine'
    
    def ready(self):
        # Register regression modules with engine
        from engine.modules import register
        register('regression', 'models.regression:RegressionModule')
        register('bayesian', 'models.bayesian_regression:BayesianRegressionModule')
        register('bma', 'models.BMA:BMAModule')
        register('anova', 'models.ANOVA:ANOVAModule')
        register('varx', 'models.VARX:VARXModule')