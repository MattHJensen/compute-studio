# if you want to use a user besides postgres,
# run `DATABASE_USER=yourusername source webapp_env.sh`
export DATABASE_NAME=comp_local_database
if [ -z ${DATABASE_USER+x} ]
then
    echo using database username postgres
    export DATABASE_USER=postgres
else
    echo using database username $DATABASE_USER
fi

export DATABASE_URL=postgresql://localhost/$DATABASE_NAME
if ! psql -l | grep $DATABASE_NAME
then
    echo creating database $DATABASE_NAME under username $DATABASE_USER
    createdb $DATABASE_NAME -U $DATABASE_USER
fi

# set stripe use to False by default
export USE_STRIPE=False

export NUM_BUDGET_YEARS=10
export DEBUG=True

export WORKERS=127.0.0.1:5050

export LOCAL=True