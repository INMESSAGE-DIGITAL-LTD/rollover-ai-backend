<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

class CreateHighlightsTable extends Migration
{
    /**
     * Run the migrations.
     *
     * @return void
     */
    public function up()
    {
        Schema::create('highlights', function (Blueprint $table) {
            $table->id();

            $table->string('title', 191);
            $table->string('league', 191);
            $table->string('url', 191);
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
        Schema::dropIfExists('highlights');
    }
}
