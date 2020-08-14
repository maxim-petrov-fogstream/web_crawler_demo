 <?php
    require_once "/var/www/localhost.com/lib/Zend/Debug.php";
    ini_set('display_errors', '1');
    function getProducts()
    {
        $db = mssql_connect("192.168.0.115","_MT_USER","mt12051984") or die('error connected');

        $q = mssql_query("EXEC cladata.dbo.spCS_mt_PriceInet");
        $res = array();

        while ($row = mssql_fetch_array($q, MSSQL_NUM))
        {
            $res[ $row[0] ] = array(
                'sku'  => $row[0],
                'name' => $row[1],
                'inet' => ( isset( $row[4] ) && $row[4] == 1 )? $row[3]:$row[2],
                'qty'  => 0,
                'opt'  => 0,
                'sale' => 0,
            );
        }

        $q = mssql_query("EXEC cladata.dbo.spCS_mt_GetShopsRests") or die('111');
        while ($row = mssql_fetch_array($q, MSSQL_NUM))
        {
            if( !isset( $res[ $row[2] ] ) )
            {
                $res[ $row[2] ] = array(
                    'sku'  => $row[2],
                    'name' => $row[3],
                    'inet' => 0,
                );
            }
            $res[ $row[2] ]['qty'] = $row[4];
            $res[ $row[2] ]['opt'] = $row[5];
            $res[ $row[2] ]['sale'] = (( isset( $row[7] ) && $row[7] == 0 )? $row[6]:$row[7]);
        }
        mssql_close( $db );

        foreach( $res as $item )
        {
            $sql = sprintf( "INSERT INTO tp_syncro(`sku`, `name`, `qty`, `price_opt`, `price_sale`, `price_inet`) VALUES( '%s', '%s', '%d', '%f', '%f', '%f' )",
                $item['sku'],
                trim( iconv('windows-1251', 'UTF-8', $item['name'] ) ),
                $item['qty'],
                $item['opt'],
                $item['sale'],
                $item['inet']
            );
            if (! mysql_query($sql) ) {
                $sql = sprintf( "UPDATE tp_syncro SET name='%s', qty='%d', price_opt='%f', price_sale='%f', price_inet='%f' WHERE sku='%s'",
                    trim( iconv('windows-1251', 'UTF-8', $item['name'] ) ),
                    $item['qty'],
                    $item['opt'],
                    $item['sale'],
                    $item['inet'],
                    $item['sku']
                );
                mysql_query($sql);
            }
        }
    }

    $mysql = mysql_connect('localhost','tp_user','111111') or die("Не могу создать соединение ");
    mysql_select_db('tp') or die(mysql_error());
    mysql_query("SET character_set_results = 'utf8', character_set_client = 'utf8', character_set_connection = 'utf8', character_set_database = 'utf8', character_set_server = 'utf8'", $mysql);

    getProducts();
    mysql_close();
#    exec('python /var/www/tp/manage.py syncro_cron');

?>
