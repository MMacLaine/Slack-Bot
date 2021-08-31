# slack-bot
source: https://medium.com/developer-student-clubs-tiet/how-to-build-your-first-slack-bot-in-2020-with-python-flask-using-the-slack-events-api-4b20ae7b4f86

technical Documentation:
https://docs.google.com/document/d/13kdkliLILXGMSe6k7MT_7kJIeRnB6dx_I-HzVKoUf5Y/edit?usp=sharing

## How to run locally
 1. run_locally.sh
 2. ngrok http 80

## Deployment
This project has been deployed using the service-template.

- Push/RP on main branch
- AWS codebuild: run slack-bot-ecs-ci build with parameters, overriding the branch to main
- Check aws ECS for test-plat-slack-bot-b1e1 and wait for "Reached steady state" message
