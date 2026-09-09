import time
from app.services.agent_model_versions import process_next,recover_jobs

def main():
    recover_jobs()
    while True:
        if process_next() is None:time.sleep(2)

if __name__=='__main__':main()
