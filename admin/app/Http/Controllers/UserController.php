<?php

namespace App\Http\Controllers;

use App\Models\User;
use Illuminate\Http\Request;
use Illuminate\Validation\Rule;
use DataTables;

class UserController extends Controller
{
    /**
     * Display a listing of the resource.
     *
     * @return \Illuminate\Http\Response
     */
    public function index(Request $request)
    {

        $users = User::where('user_type', 'user')
                            ->orderBy('id', 'DESC');

        $currency = get_option('currency');

        if ($request->ajax()) {
            return DataTables::of($users)
                ->editColumn('image', function ($user) {
                    return '<img class="img-sm img-thumbnail" src="' . asset($user->image) . '">';
                })
                ->addColumn('name', function ($user) {
                    return $user->first_name;
                })
                ->editColumn('status', function ($user) {
                    return $user->status == 1 ? status(_lang('Active'), 'success') : status(_lang('In-Active'), 'danger');
                })
                ->addColumn('action', function($user){

                    $action = '<div class="dropdown">
                                    <button class="btn btn-primary btn-sm dropdown-toggle" type="button" id="dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                                        ' . _lang('Action') . '
                                    </button>
                                    <div class="dropdown-menu" aria-labelledby="dropdownMenuButton">';
                    $action .= '<a href="' . route('users.show', $user->id) . '" class="dropdown-item ajax-modal" data-title="' . _lang('Details') . '">
                                        <i class="fas fa-eye"></i>
                                        ' . _lang('Details') . '
                                    </a>';
                    // $action .= '<a href="' . route('users.edit', $user->id) . '" class="dropdown-item ajax-modal" data-title="' . _lang('Edit') . '">
                    //                     <i class="fas fa-edit"></i>
                    //                     ' . _lang('Edit') . '
                    //                 </a>';
                    // $action .= '<form action="' . route('users.destroy', $user->id) . '" method="post" class="ajax-delete">'
                    //             . csrf_field() 
                    //             . method_field('DELETE') 
                    //             . '<button type="button" class="btn-remove dropdown-item">
                    //                     <i class="fas fa-trash-alt"></i>
                    //                     ' . _lang('Delete') . '
                    //                 </button>
                    //             </form>';
                    $action .= '</div>
                            </div>';
                    return $action;
                })
                ->rawColumns(['action', 'status', 'image', 'app_unique_id'])
                ->make(true);
        }

        return view('backend.users.index', compact('users'));
    }

    /**
     * Show the form for creating a new resource.
     *
     * @return \Illuminate\Http\Response
     */
    public function create(Request $request)
    {
        if (!$request->ajax()) {
            return view('backend.users.create');
        } else {
            return view('backend.users.modal.create');
        }
    }

    /**
     * Store a newly created resource in storage.
     *
     * @param  \Illuminate\Http\Request  $request
     * @return \Illuminate\Http\Response
     */
    public function store(Request $request)
    {
        $validator = \Validator::make($request->all(), [

            'first_name' => 'required|string|max:191',
            'last_name' => 'required|string|max:191',
            'email' => 'nullable|string|email|max:191|unique:users',
            'status' => 'required',
            'password' => 'required|string|min:6|confirmed',
            'image' => 'nullable|image',

        ]);

        if ($validator->fails()) {
            if ($request->ajax()) {
                return response()->json(['result' => 'error', 'message' => $validator->errors()->all()]);
            } else {
                return back()->withErrors($validator)->withInput();
            }
        }

        $user = new User();

        $user->first_name = $request->first_name;
        $user->last_name = $request->last_name;
        $user->email = $request->email;
        $user->provider = 'email';
        $user->status = $request->status;

        if ($request->hasFile('image')) {
            $image = $request->file('image');
            $ImageName = time() . '.' . $image->getClientOriginalExtension();
            \Image::make($image)->resize(300, 300)->save(base_path('public/uploads/images/users/') . $ImageName);
            $user->image = 'public/uploads/images/users/' . $ImageName;
        }

        $user->save();

        if (!$request->ajax()) {
            return redirect('users')->with('success', _lang('Information has been added.'));
        } else {
            return response()->json(['result' => 'success', 'redirect' => 'users', 'message' => _lang('Information has been added sucessfully.')]);
        }
    }

    /**
     * Display the specified resource.
     *
     * @param  int  $id
     * @return \Illuminate\Http\Response
     */
    public function show(Request $request, $id)
    {
        $user = User::find($id);

        if (!$request->ajax()) {
            return view('backend.users.show', compact('user'));
        } else {
            return view('backend.users.modal.show', compact('user'));
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
        $user = User::find($id);

        if (!$request->ajax()) {
            return view('backend.users.edit', compact('user'));
        } else {
            return view('backend.users.modal.edit', compact('user'));
        }
    }

    /**
     * Update the specified resource in storage.
     *
     * @param  \Illuminate\Http\Request  $request
     * @param  int  $id
     * @return \Illuminate\Http\Response
     */
    public function update(Request $request, $id)
    {
        $validator = \Validator::make($request->all(), [

            'first_name' => 'required|string|max:191',
            'last_name' => 'required|string|max:191',
            'email' => [
                'nullable',
                Rule::unique('users')->ignore($id),
            ],
            'status' => 'required',
            'image' => 'nullable|image',

        ]);

        if ($validator->fails()) {
            if ($request->ajax()) {
                return response()->json(['result' => 'error', 'message' => $validator->errors()->all()]);
            } else {
                return back()->withErrors($validator)->withInput();
            }
        }

        $user = User::find($id);

        $user->first_name = $request->first_name;
        $user->last_name = $request->last_name;
        $user->email = $request->email;
        $user->status = $request->status;

        if ($request->hasFile('image')) {
            $image = $request->file('image');
            $ImageName = time() . '.' . $image->getClientOriginalExtension();
            \Image::make($image)->resize(300, 300)->save(base_path('public/uploads/images/users/') . $ImageName);
            $user->image = 'public/uploads/images/users/' . $ImageName;
        }

        $user->save();

        if (!$request->ajax()) {
            return redirect('users')->with('success', _lang('Information has been updated.'));
        } else {
            return response()->json(['result' => 'success', 'redirect' => 'users', 'message' => _lang('Information has been updated sucessfully.')]);
        }
    }

    /**
     * Remove the specified resource from storage.
     *
     * @param  int  $id
     * @return \Illuminate\Http\Response
     */
    public function destroy(Request $request, $id)
    {
        $user = User::find($id);
        $user->delete();

        if (!$request->ajax()) {
            return back()->with('success', _lang('Information has been deleted'));
        } else {
            return response()->json(['result' => 'success', 'message' => _lang('Information has been deleted sucessfully')]);
        }
    }
}
