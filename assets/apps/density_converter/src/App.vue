<template>
  <div @keyup.enter="calcDensity">
      <center>
      <div class="container"> 
      
            <label>Enter Physical Density: </label>
            <input type="text" placeholder="(kg/m3)" v-model="density" required> <br>
            <label>Enter Temperature Density: </label>
            <input type="text" placeholder="(deg C)" v-model="temp" required>  
            <br>
            <strong>Select Product: </strong>  
            <select class="product" v-model="prod">
                <option value="HSD" selected>Diesel (HSD)</option>
                <option value="MS">Petrol (MS) </option>
                <option value="SKO">Kerosene (SKO)</option>
            </select> 
            <br><br>
        
        <button class="btn btn-primary" v-on:click="calcDensity">Submit</button>
        <br>
        <button class="output" v-if="calculated"> <i class="fa fa-arrow-right" aria-hidden="true"></i> {{ displayDensity }}</button>
      </div> 
      </center>
        
    
    <center>
        <div class="container" style="background-color:#f1f1f1"> 
            <button type="button" v-on:click="resetCalc" class="cancelbtn">Reset</button> 
            <br>
            <span>*** This density is for your easy reference only. For official implications please refer the physical ASTM 53B document</span> 
        </div>
    </center> 

    
  </div>
</template>

<script>
export default {
  data () {
    return {
      density: '',
      temp: '',
      prod: 'HSD',
      displayDensity: '',
      calculated: false
    }
  },

  methods: {
        calcDensity: function(){

            var C, lower_limit, upper_limit;

            if (this.prod === 'MS'){
                C = 0.9
                lower_limit = 720
                upper_limit = 775
              } else if (this.prod === 'HSD') {
                var C = 0.7
                lower_limit = 820
                upper_limit = 855
              } else {
                C = 0.7
                lower_limit = 700
                upper_limit = 855
            }

            var d15 = parseFloat(this.density) + C*(parseFloat(this.temp) -15);
            
            if (isNaN(d15)){
                this.displayDensity = 'Input Error ! Please enter numbers only';
            } else {
                
                if (d15 > upper_limit){
                    this.displayDensity = 'Density @15 deg C is > permissible limit of ' + this.prod + ': ' + upper_limit;
                } else if(d15 < lower_limit){
                    this.displayDensity = 'Density @15 deg C is < permissible limit of ' + this.prod + ': ' + lower_limit;
                } else {
                    this.displayDensity = 'Density @ 15 deg C: ' + d15;
                }
            }

            this.calculated = true;

        },

        resetCalc: function(){
            this.calculated = false;
            this.density = '';
            this.temp = '';
            this.prod = 'HSD';
            this.displayDensity = '';

        }
    }


}
</script>

<style>
 /*set border to the form*/ 
          
    form { 
        border: 3px solid #f1f1f1; 
    } 
    /*assign full width inputs*/ 
    
    .navbar-header h4{
        margin-left: 20px;
        color: #f1f1f1;
    }



    input[type=text], 
    input[type=password] { 
        width: 60%; 
        padding: 12px 20px; 
        margin: 8px 0; 
        /* display: inline-block;  */
        border: 1px solid #ccc; 
        box-sizing: border-box; 
        border-radius: 5px;;
    } 
    /*set a style for the buttons*/ 
      
    .submit { 
        background-color: #4CAF50; 
        color: white; 
        padding: 14px 20px; 
        margin: 8px 0; 
        border: none; 
        cursor: pointer; 
        width: 40%; 
    } 

    .output {
        background-color: #073d09; 
        color: white; 
        padding: 14px 20px; 
        margin: 8px 0; 
        border-radius: 5px;
        cursor: None; 
        width: 80%;
    }
    /* set a hover effect for the button*/ 
      
    button:hover { 
        opacity: 0.8; 
    } 
    /*set extra style for the cancel button*/ 
      
    .cancelbtn { 
        width: auto; 
        padding: 10px 18px; 
        background-color: #f44336;
        border-radius: 5px; 
    } 
    /*centre the display image inside the container*/ 
      
    .imgcontainer { 
        text-align: center; 
        margin: 24px 0 12px 0; 
    } 
    /*set image properties*/ 
      
    img.avatar { 
        width: 40%; 
        border-radius: 50%; 
    } 
    /*set padding to the container*/ 
      
    .container { 
        padding: 10px; 
        border-radius: 5px;
    } 
    /*set the forgot password text*/ 
      
    span.psw { 
        float: right; 
        padding-top: 5px; 
    } 
    /*set styles for span and cancel button on small screens*/ 
      
    @media screen and (max-width: 300px) { 
        span.psw { 
            display: block; 
            float: none; 
        } 
        .cancelbtn { 
            width: 100%; 
        } 
    } 
</style>
