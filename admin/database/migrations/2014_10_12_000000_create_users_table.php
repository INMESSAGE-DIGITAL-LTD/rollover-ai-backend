<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

class CreateUsersTable extends Migration
{
    /**
     * Run the migrations.
     *
     * @return void
     */
    public function up()
    {
        Schema::create('users', function (Blueprint $table) {
            $table->id();
            
            $table->string('first_name', 100);
            $table->string('last_name', 100);
            $table->string('email', 191)->unique();
            $table->string('password', 191);
            $table->string('user_type', 100);
            $table->bigInteger('subscription_id')->default(0);
            $table->string('expired_at', 100)->nullable();
            $table->string('image', 191)->default('public/default/profile.png');
            $table->string('provider', 191)->default('email');
            $table->text('device_token')->nullable();
            $table->timestamp('email_verified_at')->nullable();
            $table->integer('status')->default(1);

            $table->rememberToken();
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     *
     * @return void
     */
    public function down()
    {
        Schema::dropIfExists('users');
    }
}
