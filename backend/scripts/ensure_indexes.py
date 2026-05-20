from app.core.database import Base, engine


def main():
    Base.metadata.create_all(bind=engine)
    print('Indexes ensured.')


if __name__ == '__main__':
    main()
