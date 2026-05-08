<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

class CreateStreamingSourcesTable extends Migration
{
    /**
     * Run the migrations.
     *
     * @return void
     */
    public function up()
    {
        Schema::create('streaming_sources', function (Blueprint $table) {
            $table->id();

            $table->bigInteger('match_id');
            $table->string('title', 191);
            $table->string('source_type', 30);
            $table->string('url', 191);
            $table->string('source_from', 30);
            $table->longText('headers')->nullable();
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
        Schema::dropIfExists('streaming_sources');
    }
}
