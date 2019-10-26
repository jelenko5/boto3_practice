# AWS and boto3 Cheat Sheet #

## Working Hours Inspector
Lambda function which is supposed to start EC2 and RDS instances during working hours and stop them during non-working
 hours(serbian timezone). 

Requirements:
- `env` tag on instances. Only instances with `env != "production"` tag will be affected
- `time` tag on instances. Defines opening and closing hours in format HH-HH
- cron job scheduler that triggers lambda function
- aws cli for local usage (configured with `~/.aws/credentials` and `~/.aws/config` files)

