#build AWS Lambda Python Base Image (ECR/Lambda connection) 
FROM public.ecr.aws/lambda/python:3.12

#Working directory - for Copy & Run
#Environment Variable
#AWS Lambda images uses ${LAMBDA_TASK_ROOT} instead of/code
WORKDIR ${LAMBDA_TASK_ROOT}

#Install dependencies for project (python)
COPY requirements.txt .

RUN pip install -r requirements.txt 

#Copy Application Code 
COPY . .

#Connect to handler function
CMD ["app.handler"]
#Name of file 
