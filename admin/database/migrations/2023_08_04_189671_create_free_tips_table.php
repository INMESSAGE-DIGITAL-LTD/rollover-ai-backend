<?php

use Illuminate\Support\Facades\Schema;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Database\Migrations\Migration;

class CreateFreeTipsTable extends Migration
{
    /**
     * Run the migrations.
     *
     * @return void
     */
    public function up()
    {
        Schema::create('free_tips', function (Blueprint $table) {
            $table->bigIncrements('id');
            
			$table->string('title', 191);
			$table->string('league', 191);
			$table->string('match_time', 30);
			$table->string('odds_value', 191);
			$table->string('result', 30);
			$table->string('team_one_name');
            $table->string('team_one_image_type');
            $table->string('team_one_url')->nullable();
            $table->string('team_one_image')->nullable();
            $table->string('team_two_name');
            $table->string('team_two_image_type');
            $table->string('team_two_url')->nullable();
            $table->string('team_two_image')->nullable();
			$table->integer('status');

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
        Schema::dropIfExists('free_tips');
    }
}
