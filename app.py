from flask import Flask, request, redirect, url_for, render_template_string, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cloud_itsm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(20)) 

class ResourceRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    resource_type = db.Column(db.String(100))
    specs = db.Column(db.String(200))
    status = db.Column(db.String(50), default="Pending")
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class ChangeRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    resource_id = db.Column(db.Integer, db.ForeignKey('resource_request.id'))
    new_specs = db.Column(db.String(200)) 
    status = db.Column(db.String(50), default="Pending")

class Maintenance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service = db.Column(db.String(100))
    scheduled_time = db.Column(db.String(100))

class BackupLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(100))
    status = db.Column(db.String(50))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

base_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Cloud ITSM</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: linear-gradient(to right, #1e3c72, #2a5298); color:white; min-height: 100vh; }
        .card { background:#ffffff; color:black; border-radius:15px; border:none; }
        .navbar { background:#0d1b2a; }
        .btn-primary { background:#0077b6; border:none; }
        .footer { margin-top:50px; text-align:center; padding-bottom: 20px; }
        .alert { border-radius: 10px; }
    </style>
</head>
<body>

<nav class="navbar navbar-expand-lg navbar-dark px-4">
    <a class="navbar-brand" href="/">Cloud ITSM</a>
    <div class="collapse navbar-collapse">
        <ul class="navbar-nav ms-auto">
            {% if current_user.is_authenticated %}
                <li class="nav-item"><a class="nav-link" href="/dashboard">Dashboard</a></li>
                {% if current_user.role == 'admin' %}
                    <li class="nav-item"><a class="nav-link text-warning" href="/admin">Admin Panel</a></li>
                    <li class="nav-item"><a class="nav-link text-info" href="/inspect_db">Database Audit</a></li>
                {% endif %}
                <li class="nav-item"><a class="nav-link" href="/logout">Logout</a></li>
            {% else %}
                <li class="nav-item"><a class="nav-link" href="/login">Login</a></li>
                <li class="nav-item"><a class="nav-link" href="/register">Register</a></li>
            {% endif %}
        </ul>
    </div>
</nav>

<div class="container mt-4">
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        {% for message in messages %}
          <div class="alert alert-info alert-dismissible fade show" role="alert">
            {{ message }}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
          </div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    {{ content | safe }}
</div>

<div class="footer">
    <hr style="width:50%; margin: 20px auto;">
    <p><h3>Cloud Infrastructure Management System </h3></p>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

@app.route('/')
def home():
    content = """
    <div class='text-center py-5'>
        <h1 class='display-4'>Cloud Infrastructure Management</h1>
        <p class='lead'>A Simulated Cloud Platform implementing ITSM Best Practices</p>
        <div class='mt-4'>
            <a href='/catalog' class='btn btn-light btn-lg px-4 me-2'>Service Catalog</a>
            <a href='/login' class='btn btn-outline-light btn-lg px-4'>Client Login</a>
        </div>
    </div>
    """
    return render_template_string(base_template, content=content)

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        hashed_pw = generate_password_hash(request.form['password'])
        user = User(username=request.form['username'], password=hashed_pw, role=request.form['role'])
        db.session.add(user)
        db.session.commit()
        flash("Account created! You can now login.")
        return redirect(url_for('login'))
    content = "<div class='card p-4 mx-auto' style='max-width:400px;'><h3>Register</h3><form method='POST'><input class='form-control mb-2' name='username' placeholder='Username' required><input type='password' class='form-control mb-2' name='password' placeholder='Password' required><select class='form-control mb-2' name='role'><option value='user'>Standard User</option><option value='admin'>System Admin</option></select><button class='btn btn-primary w-100'>Create Account</button></form></div>"
    return render_template_string(base_template, content=content)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            flash(f"Welcome back, {user.username}!")
            return redirect(url_for('dashboard'))
        flash("Invalid credentials.")
    content = "<div class='card p-4 mx-auto' style='max-width:400px;'><h3>Login</h3><form method='POST'><input class='form-control mb-2' name='username' placeholder='Username' required><input type='password' class='form-control mb-2' name='password' placeholder='Password' required><button class='btn btn-primary w-100'>Login</button></form></div>"
    return render_template_string(base_template, content=content)

@app.route('/dashboard')
@login_required
def dashboard():
    resources = ResourceRequest.query.filter_by(user_id=current_user.id).all()
    pending_changes = [c.resource_id for c in ChangeRequest.query.filter_by(status="Pending").all()]
    
    content = "<h3>Your Active Assets</h3>"
    for r in resources:
        is_locked = r.id in pending_changes
        status_text = "LOCKED (Change Pending)" if is_locked else r.status
        card_opacity = "opacity: 0.6;" if is_locked else ""
        
        content += f"""
        <div class='card p-3 mb-3 shadow-sm' style='{card_opacity}'>
            <div class='d-flex justify-content-between align-items-center'>
                <div>
                    <h5>{r.resource_type} {'🔒' if is_locked else ''}</h5>
                    <small class='text-muted'>ID: #{r.id} | Specs: {r.specs}</small>
                </div>
                <span class='badge bg-{"info" if is_locked else "success"}'>{status_text}</span>
            </div>
        </div>"""
    content += "<br><a href='/catalog' class='btn btn-light'>+ Request New</a> <a href='/change_request' class='btn btn-warning'>Modify Existing</a>"
    return render_template_string(base_template, content=content)


@app.route('/catalog')
@login_required
def catalog():
    content = """
    <div class='card p-4 shadow-sm'>
        <h3 class='text-primary mb-3'>Cloud Service Catalog</h3>
        <p class='text-muted'>Standardized ITIL Service Request Portal</p>
        <hr>
        
        <form method='POST' action='/request_resource'>
            <label class='form-label'><b>1. Select Service Category:</b></label>
            <select class='form-control mb-3' name='resource' id='resource_type' onchange="updateSpecs()">
                <optgroup label="Compute">
                    <option value='Virtual Machine'>Virtual Machine</option>
                    <option value='Kubernetes Cluster (K8s)'>Kubernetes Cluster (K8s)</option>
                    <option value='Serverless Function (Lambda)'>Serverless Function (Lambda)</option>
                </optgroup>
                <optgroup label="Storage & Database">
                    <option value='Storage Bucket (S3/Blob)'>Storage Bucket (S3/Blob)</option>
                    <option value='Managed SQL Database'>Managed SQL Database</option>
                    <option value='NoSQL Database (MongoDB)'>NoSQL Database (MongoDB)</option>
                </optgroup>
                <optgroup label="Networking & Security">
                    <option value='VPC / Virtual Network'>VPC / Virtual Network</option>
                    <option value='Load Balancer'>Load Balancer</option>
                    <option value='Firewall / Security Group'>Firewall / Security Group</option>
                </optgroup>
            </select>

            <label class='form-label'><b>2. Select Configuration (Specs):</b></label>
            <select class='form-control mb-4' name='specs' id='specs_dropdown'>
                </select>

            <button class='btn btn-primary w-100 py-2'>Submit Infrastructure Request</button>
        </form>
    </div>

    <script>
    function updateSpecs() {
        var resource = document.getElementById("resource_type").value;
        var specsDropdown = document.getElementById("specs_dropdown");
        specsDropdown.innerHTML = ""; 

        var options = {
            "Virtual Machine": ["Basic (1 vCPU, 2GB)", "Standard (2 vCPU, 4GB)", "Compute Optimized (4 vCPU, 8GB)"],
            "Kubernetes Cluster (K8s)": ["Dev (1 Node, t3.small)", "Prod (3 Nodes, High Availability)", "Auto-scaling (1-10 Nodes)"],
            "Serverless Function (Lambda)": ["128MB Memory", "512MB Memory", "2048MB Memory"],
            "Storage Bucket (S3/Blob)": ["Standard (50GB)", "Infrequent Access (200GB)", "Archive (1TB)"],
            "Managed SQL Database": ["MySQL (Small, 10GB)", "PostgreSQL (Large, 50GB)", "SQL Server (Standard)"],
            "NoSQL Database (MongoDB)": ["M10 (2GB RAM)", "M30 (8GB RAM)", "M50 (Dedicated Cluster)"],
            "VPC / Virtual Network": ["Small (10.0.1.0/24)", "Corporate (10.0.0.0/16)", "Hybrid (Connected via VPN)"],
            "Load Balancer": ["Public (External)", "Internal (Private)", "Network-Level (High Speed)"],
            "Firewall / Security Group": ["Allow Web (80/443)", "Allow SSH (22)", "Custom Security Rules"]
        };

        var selectedOptions = options[resource] || [];

        selectedOptions.forEach(function(opt) {
            var el = document.createElement("option");
            el.textContent = opt;
            el.value = opt;
            specsDropdown.appendChild(el);
        });
    }

    // Initial load
    window.onload = updateSpecs;
    </script>
    """
    return render_template_string(base_template, content=content)

@app.route('/request_resource', methods=['POST'])
@login_required
def request_resource():
    req = ResourceRequest(resource_type=request.form['resource'], specs=request.form['specs'], user_id=current_user.id)
    db.session.add(req)
    db.session.commit()
    flash("Resource request submitted for approval.")
    return redirect(url_for('dashboard'))


@app.route('/change_request', methods=['GET','POST'])
@login_required
def change_request():
    user_resources = ResourceRequest.query.filter_by(user_id=current_user.id, status="Approved").all()
    
    if request.method == 'POST':
        resource_id = request.form.get('resource_id')
        new_specs = request.form.get('new_specs')

        ch = ChangeRequest(resource_id=resource_id, new_specs=new_specs, status="Pending")
        db.session.add(ch)
        db.session.commit()
        flash("Request for Change (RFC) submitted to the Change Advisory Board.")
        return redirect(url_for('dashboard'))

    if not user_resources:
        content = "<div class='card p-4'><h3>No Active Resources</h3><p>You need an approved resource before you can request a change.</p><a href='/catalog' class='btn btn-primary'>Go to Catalog</a></div>"
        return render_template_string(base_template, content=content)

    content = """
    <div class='card p-4 shadow'>
        <h3 class='text-warning'>Request Infrastructure Change</h3>
        <p class='text-muted small'>Standardized Change Management (ITIL v4)</p>
        <hr>
        <form method='POST'>
            <label class='form-label'><b>1. Select Resource to Modify:</b></label>
            <select class='form-control mb-3' name='resource_id' id='res_selector' onchange="syncResourceType()">
    """
    for r in user_resources:
        content += f"<option value='{r.id}' data-type='{r.resource_type}'>ID: {r.id} | {r.resource_type} ({r.specs})</option>"

    content += """
            </select>

            <input type="hidden" id="resource_type_hidden">

            <label class='form-label'><b>2. Select New Configuration:</b></label>
            <select class='form-control mb-4' name='new_specs' id='change_specs_drop'>
                </select>

            <button class='btn btn-warning w-100 py-2'>Submit Change Request</button>
        </form>
    </div>

    <script>
    function syncResourceType() {
        // Get the 'data-type' attribute of the selected option
        var selector = document.getElementById('res_selector');
        var selectedOption = selector.options[selector.selectedIndex];
        var resType = selectedOption.getAttribute('data-type');
        
        updateChangeSpecs(resType);
    }

    function updateChangeSpecs(resource) {
        var specsDropdown = document.getElementById("change_specs_drop");
        specsDropdown.innerHTML = ""; 

        var options = {
            "Virtual Machine": ["Basic (1 vCPU, 2GB)", "Standard (2 vCPU, 4GB)", "Compute Optimized (4 vCPU, 8GB)"],
            "Kubernetes Cluster (K8s)": ["Dev (1 Node, t3.small)", "Prod (3 Nodes, High Availability)", "Auto-scaling (1-10 Nodes)"],
            "Serverless Function (Lambda)": ["128MB Memory", "512MB Memory", "2048MB Memory"],
            "Storage Bucket (S3/Blob)": ["Standard (50GB)", "Infrequent Access (200GB)", "Archive (1TB)"],
            "Managed SQL Database": ["MySQL (Small, 10GB)", "PostgreSQL (Large, 50GB)", "SQL Server (Standard)"],
            "NoSQL Database (MongoDB)": ["M10 (2GB RAM)", "M30 (8GB RAM)", "M50 (Dedicated Cluster)"],
            "VPC / Virtual Network": ["Small (10.0.1.0/24)", "Corporate (10.0.0.0/16)", "Hybrid (Connected via VPN)"],
            "Load Balancer": ["Public (External)", "Internal (Private)", "Network-Level (High Speed)"],
            "Firewall / Security Group": ["Allow Web (80/443)", "Allow SSH (22)", "Custom Security Rules"]
        };

        var selectedOptions = options[resource] || [];
        selectedOptions.forEach(function(opt) {
            var el = document.createElement("option");
            el.textContent = opt;
            el.value = opt;
            specsDropdown.appendChild(el);
        });
    }

    // Initial load to set the first resource's dropdown
    window.onload = syncResourceType;
    </script>
    """
    return render_template_string(base_template, content=content)

@app.route('/admin')
@login_required
def admin():
    if current_user.role != 'admin': 
        return redirect(url_for('dashboard'))
    
    reqs = ResourceRequest.query.all()
    changes = ChangeRequest.query.all()
    maintenance_list = Maintenance.query.all()
    backups = BackupLog.query.order_by(BackupLog.id.desc()).limit(5).all()
    
    content = "<h2 class='mb-4 border-bottom pb-2 text-info'>System Administration Console</h2>"
    
    content += "<div class='mb-5'><h4><span class='badge bg-primary me-2'>1</span> New Service Requests</h4>"
    pending_reqs = [r for r in reqs if r.status == "Pending"]
    for r in pending_reqs:
        user = User.query.get(r.user_id)
        content += f"""
        <div class='card p-3 mb-3 shadow-sm border-start border-primary border-4'>
            <strong>{r.resource_type}</strong> <span class='text-muted small'>by {user.username}</span><br>
            <code>Specs: {r.specs}</code><br>
            <a href='/approve_resource/{r.id}' class='btn btn-success btn-sm mt-2 w-25'>Approve</a>
        </div>"""
    content += "</div>"

    content += "<div class='mb-5'><h4><span class='badge bg-warning text-dark me-2'>2</span> Change Requests (RFC)</h4>"
    pending_changes = [c for c in changes if c.status == "Pending"]
    
    for c in pending_changes:
        original_res = ResourceRequest.query.get(c.resource_id)
        owner = User.query.get(original_res.user_id) if original_res else None
        
        content += f"""
        <div class='card p-3 mb-3 shadow-sm border-start border-warning border-4'>
            <div class='row'>
                <div class='col-md-8'>
                    <strong>User: {owner.username if owner else 'Unknown'}</strong><br>
                    <span class='badge bg-secondary'>Type: {original_res.resource_type if original_res else 'N/A'}</span>
                    <div class='mt-2'>
                        <span class='text-danger'>● Previous: {original_res.specs if original_res else 'N/A'}</span><br>
                        <span class='text-success'>➜ Proposed: {c.new_specs}</span>
                    </div>
                </div>
                <div class='col-md-4 text-end'>
                    <a href='/approve_change/{c.id}' class='btn btn-primary btn-sm w-100 mb-2'>Approve & Update</a>
                    <small class='text-muted italic'>Original Asset ID: #{c.resource_id}</small>
                </div>
            </div>
        </div>"""
    content += "</div>"

    content += """
    <div class='mb-5'>
        <h4><span class='badge bg-danger me-2'>3</span> Availability Management</h4>
        <div class='card p-4 bg-light text-dark mb-4'>
            <h6>Schedule New Maintenance Window</h6>
            <form method='POST' action='/schedule_maintenance' class='row g-3'>
                <div class='col-md-5'><input name='service' class='form-control' placeholder='Service Name' required></div>
                <div class='col-md-4'><input name='time' class='form-control' placeholder='Scheduled Time' required></div>
                <div class='col-md-3'><button class='btn btn-danger w-100'>Broadcast Schedule</button></div>
            </form>
        </div>
    """
    if maintenance_list:
        content += "<h6>Current Schedule:</h6>"
        for m in maintenance_list:
            content += f"<div class='alert alert-dark py-2 mb-2 small'>🛠️ <strong>{m.service}</strong> is scheduled for <strong>{m.scheduled_time}</strong></div>"
    content += "</div><hr class='my-4' style='opacity: 0.1;'>"

    content += """
    <div class='mb-5'>
        <h4><span class='badge bg-info text-dark me-2'>4</span> Service Continuity</h4>
        <div class='d-flex justify-content-between align-items-center mb-3'>
            <span>System Backup Logs (ITIL Disaster Recovery)</span>
            <a href='/backup' class='btn btn-info btn-sm'>Run Manual Backup</a>
        </div>
    """
    for b in backups:
        content += f"<div class='text-light small border-bottom border-secondary mb-1 pb-1'>✅ Backup {b.status}: {b.date}</div>"
    content += "</div>"
    
    return render_template_string(base_template, content=content)

@app.route('/approve_resource/<int:id>')
@login_required
def approve_resource(id):
    if current_user.role == "admin":
        r = ResourceRequest.query.get(id)
        r.status = "Approved"
        db.session.commit()
        flash(f"Resource {id} provisioned.")
    return redirect(url_for('admin'))

@app.route('/approve_change/<int:id>')
@login_required
def approve_change(id):
    if current_user.role == "admin":
        c = ChangeRequest.query.get(id)
        c.status = "Approved"
        r = ResourceRequest.query.get(c.resource_id)
        if r: r.specs = c.new_specs
        db.session.commit()
        flash("Infrastructure change applied successfully.")
    return redirect(url_for('admin'))

@app.route('/schedule_maintenance', methods=['POST'])
@login_required
def schedule_maintenance():
    if current_user.role == "admin":
        service = request.form.get('service')
        time = request.form.get('time')
        new_m = Maintenance(service=service, scheduled_time=time)
        db.session.add(new_m)
        db.session.commit()
        flash(f"Maintenance window for {service} has been broadcasted.")
    return redirect(url_for('admin'))

@app.route('/backup')
@login_required
def backup():
    log = BackupLog(date=str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M")), status="Success")
    db.session.add(log)
    db.session.commit()
    flash("System Backup Completed.")
    return redirect(url_for('admin'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect('/')

@app.route('/inspect_db')
@login_required
def inspect_db():
    if current_user.role != 'admin':
        flash("Access Denied!")
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    
    content = """
    <div class='card p-4 shadow'>
        <h3 class='text-primary mb-3'>CMDB / Data Audit Report</h3>
        <p class='text-muted small'>This view represents the Configuration Management Database (CMDB) state.</p>
        <table class='table table-hover mt-3'>
            <thead class='table-dark'>
                <tr>
                    <th>User ID</th>
                    <th>Username</th>
                    <th>Role</th>
                    <th>Associated Services & Status</th>
                </tr>
            </thead>
            <tbody>
    """
    
    admins = [u for u in users if u.role == 'admin']
    customers = [u for u in users if u.role != 'admin']

    content = "<div class='card p-4 shadow'><h3>System Audit: User Roles & Assets</h3>"

    content += "<h5 class='text-danger mt-3'>Privileged Accounts (Admins)</h5>"
    content += "<ul class='list-group mb-4'>"
    for a in admins:
        content += f"<li class='list-group-item bg-light'>👑 <strong>{a.username}</strong> - Full System Access</li>"
    content += "</ul>"

    content += "<h5 class='text-primary'>Standard Service Users</h5>"
    content += "<table class='table table-sm table-hover'><thead><tr><th>Username</th><th>Active Services</th></tr></thead><tbody>"
    
    for u in customers:
        services = ResourceRequest.query.filter_by(user_id=u.id).all()
        if services:
            service_list = ", ".join([f"{s.resource_type}" for s in services])
        else:
            service_list = "<span class='text-muted'>No Services</span>"
        content += f"<tr><td><strong>{u.username}</strong></td><td>{service_list}</td></tr>"
    
    content += """
            </tbody>
        </table>
        <div class='mt-4 border-top pt-3'>
            <a href='/admin' class='btn btn-outline-secondary btn-sm'>Back to Admin Control Tower</a>
        </div>
    </div>
    """
    return render_template_string(base_template, content=content)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username="Meghana").first():
            db.session.add(User(username="Meghana", password=generate_password_hash("meghana0710"), role="admin"))
        
        if not User.query.filter_by(username="user1").first():
            user1 = User(username="user1", password=generate_password_hash("user123"), role="user")
            db.session.add(user1)
            db.session.commit() 
            
            if not ResourceRequest.query.filter_by(user_id=user1.id).first():
                db.session.add(ResourceRequest(resource_type="Virtual Machine", specs="Standard (2 vCPU, 4GB)", status="Approved", user_id=user1.id))
                db.session.add(ResourceRequest(resource_type="Storage Bucket (S3)", specs="Standard (50GB)", status="Pending", user_id=user1.id))

        if not User.query.filter_by(username="user2").first():
            user2 = User(username="user2", password=generate_password_hash("user234"), role="user")
            db.session.add(user2)
            db.session.commit()
         
            if not Maintenance.query.first():
                db.session.add(Maintenance(service="Main Database", scheduled_time="Sunday 02:00 AM"))

        db.session.commit()
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

