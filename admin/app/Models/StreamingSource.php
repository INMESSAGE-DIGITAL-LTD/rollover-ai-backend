<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class StreamingSource extends Model
{
    use HasFactory;

    /**
     * The attributes that should be hidden for serialization.
     *
     * @var array<int, string>
     */
    protected $hidden = [
        'channel_id',
        'status',
        'created_at',
        'updated_at',
    ];
    
    public function getHeadersAttribute($data)
    {
        if($this->source_from == 'aesport'){
            $headers = '{
                "Origin": "https://aesport.tv",
                "Referer": "https://aesport.tv/",
                "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Mobile Safari/537.36"
            }';
            
            
            return $headers;
        }elseif($this->source_from == 'bingsport'){
            $headers = '{
                "access-control-allow-origin": "*",
                "Referer": "https://live-streamfootball.com/"
            }';
            
            return $headers;
        }
        return null;
    }
}
