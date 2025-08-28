import shutil
import os

files_to_move = [
    ("c:\\Users\\Vincent_Pereira\\Projects\\Algo_Trading_Projects\\Trae\\Algorithmic Trading System\\ai_assistant\\financial_nlp_models.py", "c:\\Users\\Vincent_Pereira\\Projects\\Algo_Trading_Projects\\Trae\\Algorithmic Trading System\\ai_assistant\\models\\financial_nlp_models.py"),
    ("c:\\Users\\Vincent_Pereira\\Projects\\Algo_Trading_Projects\\Trae\\Algorithmic Trading System\\ai_assistant\\forecasting_models.py", "c:\\Users\\Vincent_Pereira\\Projects\\Algo_Trading_Projects\\Trae\\Algorithmic Trading System\\ai_assistant\\models\\forecasting_model_factory.py"),
    ("c:\\Users\\Vincent_Pereira\\Projects\\Algo_Trading_Projects\\Trae\\Algorithmic Trading System\\ai_assistant\\lstm_predictor.py", "c:\\Users\\Vincent_Pereira\\Projects\\Algo_Trading_Projects\\Trae\\Algorithmic Trading System\\ai_assistant\\models\\lstm_predictor.py"),
    ("c:\\Users\\Vincent_Pereira\\Projects\\Algo_Trading_Projects\\Trae\\Algorithmic Trading System\\ai_assistant\\stock_prediction_models.py", "c:\\Users\\Vincent_Pereira\\Projects\\Algo_Trading_Projects\\Trae\\Algorithmic Trading System\\ai_assistant\\models\\stock_prediction_models.py"),
    ("c:\\Users\\Vincent_Pereira\\Projects\\Algo_Trading_Projects\\Trae\\Algorithmic Trading System\\ai_assistant\\model_training.py", "c:\\Users\\Vincent_Pereira\\Projects\\Algo_Trading_Projects\\Trae\\Algorithmic Trading System\\ai_assistant\\models\\model_trainer.py"),
    ("c:\\Users\\Vincent_Pereira\\Projects\\Algo_Trading_Projects\\Trae\\Algorithmic Trading System\\ai_assistant\\tools.py", "c:\\Users\\Vincent_Pereira\\Projects\\Algo_Trading_Projects\\Trae\\Algorithmic Trading System\\ai_assistant\\tools\\agent_tools.py")
]

for src, dst in files_to_move:
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        print(f"Moved {src} to {dst}")
    except Exception as e:
        print(f"Error moving {src} to {dst}: {e}")
