<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class Highlight extends Model
{
    use HasFactory;

    /**
     * The attributes that are mass assignable.
     *
     * @var array
     */
    protected $appends = [
         'team_one_display_image',
         'team_two_display_image',
    ];

    /**
     * The attributes that should be hidden for serialization.
     *
     * @var array<int, string>
     */
    protected $hidden = [
        'status',
        'created_at',
        'updated_at',
        'team_one_image_type',
        'team_one_url',
        'team_one_image',
        'team_two_image_type',
        'team_two_url',
        'team_two_image',
    ];

    public function getTeamOneDisplayImageAttribute()
    {
        if($this->team_one_image_type == 'url'){
            return $this->team_one_url;
        }else if($this->team_one_image_type == 'image'){
            return asset($this->team_one_image);
        }   
        return asset('public/default/default-team.png'); 
    }

    public function getTeamTwoDisplayImageAttribute()
    {
        if($this->team_two_image_type == 'url'){
            return $this->team_two_url;
        }else if($this->team_two_image_type == 'image'){
            return asset($this->team_two_image);
        }   
        return asset('public/default/default-team.png'); 
    }
}
