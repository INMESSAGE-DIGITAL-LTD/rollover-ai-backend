<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class LiveMatch extends Model
{
    use HasFactory;
    
	/**
     * The table associated with the model.
     *
     * @var string
     */
    protected $table = 'live_matches';

    /**
     * The attributes that are mass assignable.
     *
     * @var array
     */
    protected $fillable = [
        'name', 'category_id', 'description', 'image', 'status', 
    ];
    
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
        'position',
        'created_by',
        'updated_by',
    ];

    /**
     * Display a listing of the resource.
     *
     * @return \Illuminate\Http\Response
     */
    public function streamingSources()
    {
        return $this->hasMany('App\Models\StreamingSource', 'match_id', 'id');
    }

    public function getMatchTime2Attribute()
    {
        $date = \Carbon\Carbon::createFromTimestamp($this->match_time)->format('Y-m-d H:i');
        return $date;
    }

    public function getMatchTime3Attribute()
    {
        $date = \Carbon\Carbon::createFromTimestamp($this->match_time)->format('d-M-Y / h:i A');
        return $date;
    }



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
