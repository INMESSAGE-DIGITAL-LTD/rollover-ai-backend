<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class Notification extends Model
{
    use HasFactory;

    public function getCreatedAtAttribute($value)
    {
        return date("Y-m-d H:i:s", strtotime($value));
    }
}
