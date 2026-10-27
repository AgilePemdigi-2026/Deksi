FROM php:8.3-cli

WORKDIR /var/www/html

RUN apt-get update && apt-get install -y \
    git \
    unzip \
    libpq-dev \
    libicu-dev \
    libonig-dev \
    libzip-dev \
    && docker-php-ext-configure pgsql --with-pgsql=/usr/local \
    && docker-php-ext-install pdo_pgsql pgsql zip bcmath \
    && curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer

COPY composer.json composer.lock* ./
RUN composer install --no-interaction --prefer-dist --no-progress --no-scripts || true

COPY . .

RUN chmod +x docker-entrypoint.sh
RUN cp -n .env.example .env || true
RUN php artisan key:generate --force || true

EXPOSE 8001

ENTRYPOINT ["./docker-entrypoint.sh"]
