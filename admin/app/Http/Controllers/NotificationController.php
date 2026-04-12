<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Notification;
use App\Models\AppModel;
use DataTables;

class NotificationController extends Controller
{

    /**
     * Display a listing of the resource.
     *
     * @return \Illuminate\Http\Response
     */
    public function index(Request $request)
    {
        $notifications = Notification::where('app', 'football_app')->orderBy('id', 'DESC');

        if ($request->ajax()) {
            return DataTables::of($notifications)
                ->addColumn('action', function($notification){

                    $action = '<div class="dropdown">
                                    <button class="btn btn-primary btn-sm dropdown-toggle" type="button" id="dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                                        ' . _lang('Action') . '
                                    </button>
                                    <div class="dropdown-menu" aria-labelledby="dropdownMenuButton">';
                    $action .= '<a href="' . route('notifications.edit', $notification->id) . '" class="dropdown-item">
                                        ' . _lang('Resend') . '
                                    </a>';
                    $action .= '<form action="' . route('notifications.destroy', $notification->id) . '" method="post" class="ajax-delete">'
                                . csrf_field() 
                                . method_field('DELETE') 
                                . '<button type="button" class="btn-remove dropdown-item">
                                        ' . _lang('Delete') . '
                                    </button>
                                </form>';
                    $action .= '</div>
                            </div>';
                    return $action;
                })
                ->setRowId(function ($notification) {
                    return "row_" . $notification->id;
                })
                ->rawColumns(['action'])
                ->make(true);
        }

        return view('backend.notifications.index', compact('notifications'));
    }

    public function create()
    {
        return view('backend.notifications.create');
    }

    public function store(Request $request)
    {

        $validator = \Validator::make($request->all(), [

            'title' => 'required|string|max:191',
            'body' => 'required',
            'image_type' => 'required|string|max:20',
            'image_url' => 'nullable|required_if:image_type,url|url',
            'image' => 'required_if:image_type,image|image',
            'action_url' => 'nullable|url|max:191',

        ]);

        if ($validator->fails()) {
            if ($request->ajax()) {
                return response()->json(['result' => 'error', 'message' => $validator->errors()->all()]);
            } else {
                return back()->withErrors($validator)->withInput();
            }
        }

        $image = '';

        $notification = new Notification();

        $notification->title = $request->title;
        $notification->message = $request->body;
        $notification->image_type = $request->image_type;
        $notification->image_url = $request->image_url;
        $notification->action_url = $request->action_url;
        $notification->app = 'football_app';

        if($request->hasFile('image')){
            $file = $request->file('image');
            $file_name = time() . '.' . $file->getClientOriginalExtension();
            $file_path = 'public/uploads/images/notifications/';
            $file->move(base_path($file_path), $file_name);
            $notification->image = $file_path . $file_name;
        }

        $notification->save();

        if($request->image_type == 'url'){
            $image = $request->image_url;
        }elseif ($request->image_type == 'image') {
            $image = asset($notification->image);
        }
        $notification->image = $image;

        $additional_data = [
            'action_url' => $notification->action_url,
        ];

        send_notification($notification, $additional_data);

        if (!$request->ajax()) {
            return redirect('notifications')->with('success', _lang('Notification sent!'));
        } else {
            return response()->json(['result' => 'success', 'redirect' => url('/notifications'), 'message' => _lang('Notification sent!')]);
        }
    }

    /**
     * Show the form for editing the specified resource.
     *
     * @param  int  $id
     * @return \Illuminate\Http\Response
     */
    public function edit(Request $request, $id)
    {
        $notification = Notification::find($id);

        return view('backend.notifications.edit', compact('notification'));
    }

    /**
     * Remove the specified resource from storage.
     *
     * @param  int  $id
     * @return \Illuminate\Http\Response
     */
    public function destroy(Request $request, $id)
    {
        $notification = Notification::find($id);
        $notification->delete();

        if (!$request->ajax()) {
            return back()->with('success', _lang('Information has been deleted'));
        } else {
            return response()->json(['result' => 'success', 'message' => _lang('Information has been deleted sucessfully')]);
        }
    }

    /**
     * Remove the specified resource from storage.
     *
     * @param  int  $id
     * @return \Illuminate\Http\Response
     */
    public function deleteall(Request $request)
    {
        $notification = Notification::truncate();

        if (!$request->ajax()) {
            return back()->with('success', _lang('Information has been deleted'));
        } else {
            return response()->json(['result' => 'success', 'message' => _lang('Information has been deleted sucessfully')]);
        }
    }
}
