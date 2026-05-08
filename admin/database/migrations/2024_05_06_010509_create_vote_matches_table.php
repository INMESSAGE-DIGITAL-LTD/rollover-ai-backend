<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

class CreateVoteMatchesTable extends Migration
{
    /**
     * Run the migrations.
     *
     * @return void
     */
    public function up()
    {
        Schema::create('vote_matches', function (Blueprint $table) {
            $table->id();
            
            $table->string('match_id');
            $table->string('league');
            $table->string('league_image')->nullable();
            $table->string('team_one_name');
            $table->string('team_one_image')->nullable();
            $table->string('team_two_name');
            $table->string('team_two_image')->nullable();
            
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
        Schema::dropIfExists('vote_matches');
    }
}
