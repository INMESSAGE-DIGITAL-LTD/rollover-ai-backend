<?php

use Illuminate\Support\Facades\Schema;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Database\Migrations\Migration;

class CreateLiveMatchesTable extends Migration
{
    /**
     * Run the migrations.
     *
     * @return void
     */
    public function up()
    {
        Schema::create('live_matches', function (Blueprint $table) {
            $table->bigIncrements('id');
            
			$table->string('match_time');
            $table->string('match_title');
            $table->string('team_one_name');
            $table->string('team_one_image_type');
            $table->string('team_one_url')->nullable();
            $table->string('team_one_image')->nullable();
            $table->string('team_two_name');
            $table->string('team_two_image_type');
            $table->string('team_two_url')->nullable();
            $table->string('team_two_image')->nullable();
            $table->bigInteger('position')->default(99999999999); 
            $table->integer('created_by');
            $table->integer('updated_by')->nullable();
            $table->integer('status')->default(1);

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
        Schema::dropIfExists('live_matches');
    }
}
