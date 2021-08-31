# technical Documentation:
TBA

## How to run locally
 1. run_locally.sh
 2. ngrok http 80/8086 (edit as needed)

## Deployment
This project has been deployed using the service-template.

- Push/RP on main branch
- AWS codebuild: run x build with parameters, overriding the branch to main
- Check aws ECS for x and wait for "Reached steady state" message
